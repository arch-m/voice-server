;;; qwen-voice.el --- TTS y ASR con modelos Qwen3 -*- lexical-binding: t; -*-

;; Copyright (C) 2026

;; Author: Claude
;; Keywords: multimedia, convenience, speech
;; Version: 2.0.0
;; Package-Requires: ((emacs "27.1") (plz "0.7"))

;; This file is not part of GNU Emacs.

;;; Commentary:

;; Este paquete proporciona integración con servidores Qwen3 para
;; text-to-speech (TTS) y automatic speech recognition (ASR).
;;
;; ARQUITECTURA:
;; TTS y ASR corren en servidores separados debido a conflictos de
;; dependencias (diferentes versiones de transformers):
;;   - TTS: http://localhost:8002 (proyecto uv server/)
;;   - ASR: http://localhost:8003 (proyecto uv server/asr-service/)
;;
;; Requiere:
;; - plz.el para peticiones HTTP
;; - PulseAudio (parecord, paplay) para captura/reproducción de audio
;; - Servidores FastAPI corriendo con los modelos Qwen3
;;
;; Comandos principales:
;; - `qwen-voice-tts-region': Lee en voz alta la región seleccionada
;; - `qwen-voice-tts-buffer': Lee el buffer completo
;; - `qwen-voice-asr-record': Graba audio y lo transcribe
;; - `qwen-voice-asr-file': Transcribe un archivo de audio
;; - `qwen-voice-health-check': Verifica estado de los servidores

;;; Code:

(require 'cl-lib)
(require 'plz)
(require 'json)

;;; Variables de configuración

(defgroup qwen-voice nil
  "Integración con servidores Qwen3 TTS y ASR."
  :group 'multimedia
  :prefix "qwen-voice-")

(defcustom qwen-voice-tts-url "http://localhost:8002"
  "URL del servidor TTS (Qwen3-TTS)."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-asr-url "http://localhost:8003"
  "URL del servidor ASR (Qwen3-ASR).
Nota: ASR corre en puerto separado por conflicto de dependencias."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-language "Spanish"
  "Idioma por defecto para TTS y ASR."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-speaker "Vivian"
  "Voz por defecto para TTS."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-temp-directory temporary-file-directory
  "Directorio para archivos temporales de audio e imágenes."
  :type 'directory
  :group 'qwen-voice)

(defcustom qwen-voice-tts-output-file nil
  "Ruta para guardar el archivo TTS generado.
Si es nil, usa archivo temporal que se borra después de reproducir.
Si es una ruta, guarda el audio ahí y no lo borra."
  :type '(choice (const :tag "Archivo temporal (se borra)" nil)
                 (file :tag "Ruta fija"))
  :group 'qwen-voice)

(defcustom qwen-voice-record-command "parecord"
  "Comando para grabar audio."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-play-command "paplay"
  "Comando para reproducir audio."
  :type 'string
  :group 'qwen-voice)

(defcustom qwen-voice-record-duration 5
  "Duración por defecto de grabación en segundos."
  :type 'integer
  :group 'qwen-voice)

;;; Variables internas

(defvar qwen-voice--recording-process nil
  "Proceso de grabación actual.")

(defvar qwen-voice--playback-process nil
  "Proceso de reproducción actual.")

;;; Funciones auxiliares

(defun qwen-voice--format-error (err)
  "Extrae mensaje de error de ERR (plz-error o cualquier otro)."
  (cond
   ((and (cl-struct-p err) (fboundp 'plz-error-message))
    (or (plz-error-message err) "Error desconocido"))
   ((and (listp err) (plist-get err :curl-error))
    (format "curl error: %s" (plist-get err :curl-error)))
   ((and (listp err) (plist-get err :response))
    (let ((resp (plist-get err :response)))
      (or (and (listp resp) (plist-get resp :body))
          (format "%s" resp))))
   (t (format "%s" err))))

(defun qwen-voice--temp-file (extension)
  "Genera un nombre de archivo temporal con EXTENSION."
  (expand-file-name
   (format "qwen-voice-%s.%s" (format-time-string "%Y%m%d-%H%M%S") extension)
   qwen-voice-temp-directory))

(defun qwen-voice--record-audio (output-file &optional duration)
  "Graba audio a OUTPUT-FILE por DURATION segundos.
Si DURATION es nil, usa `qwen-voice-record-duration'.
Retorna el proceso de grabación."
  (let* ((dur (or duration qwen-voice-record-duration))
         (args (list "--file-format=wav"
                     "--rate=16000"
                     "--channels=1"
                     (format "--process-time=%d" dur)
                     output-file)))
    (message "Grabando por %d segundos... (C-g para detener)" dur)
    (setq qwen-voice--recording-process
          (apply #'start-process "qwen-voice-record"
                 nil qwen-voice-record-command args))))

(defun qwen-voice--stop-recording ()
  "Detiene la grabación actual."
  (when (and qwen-voice--recording-process
             (process-live-p qwen-voice--recording-process))
    (interrupt-process qwen-voice--recording-process)
    (setq qwen-voice--recording-process nil)))

(defun qwen-voice--play-audio (audio-file &optional callback)
  "Reproduce AUDIO-FILE.
Llama a CALLBACK cuando termine la reproducción."
  (message "Reproduciendo audio...")
  (setq qwen-voice--playback-process
        (make-process
         :name "qwen-voice-play"
         :command (list qwen-voice-play-command audio-file)
         :sentinel (lambda (proc event)
                     (when (string-match-p "finished" event)
                       (message "Reproducción completada")
                       (when callback (funcall callback)))))))

(defun qwen-voice--tts-request (text callback &optional output-path)
  "Envía TEXT al endpoint TTS y llama a CALLBACK con el archivo WAV.
Si OUTPUT-PATH es dado, guarda el audio ahí. Si no, usa
`qwen-voice-tts-output-file' o un archivo temporal."
  (let ((output-file (or output-path
                         qwen-voice-tts-output-file
                         (qwen-voice--temp-file "wav")))
        (url (concat qwen-voice-tts-url "/tts")))
    (message "Generando audio...")
    (plz 'post url
      :headers '(("Content-Type" . "application/json"))
      :body (json-encode
             `(("text" . ,text)
               ("language" . ,qwen-voice-language)
               ("speaker" . ,qwen-voice-speaker)
               ("instruct" . "")))
      :as `(file ,output-file)
      :then (lambda (_)
              (if (and (file-exists-p output-file)
                       (> (file-attribute-size (file-attributes output-file)) 44))
                  (with-temp-buffer
                    (insert-file-contents-literally output-file nil 0 4)
                    (if (string= (buffer-string) "RIFF")
                        (progn
                          (message "Audio generado")
                          (funcall callback output-file))
                      (with-temp-buffer
                        (insert-file-contents output-file)
                        (let ((json-object-type 'alist)
                              (response (json-read-from-string (buffer-string))))
                          (message "Error TTS: %s"
                                   (or (alist-get 'detail response) "Error desconocido")))
                        (delete-file output-file))))
                (message "Error TTS: archivo de audio vacío")))
      :else (lambda (err)
              (message "Error TTS: %s" (qwen-voice--format-error err))))))

(defun qwen-voice--asr-request (audio-file callback)
  "Envía AUDIO-FILE al endpoint ASR y llama a CALLBACK con el texto."
  (let ((url (concat qwen-voice-asr-url "/asr")))
    (message "Transcribiendo audio...")
    (let* ((output-buffer (generate-new-buffer " *qwen-asr-output*"))
           (proc (start-process
                  "qwen-voice-asr" output-buffer
                  "curl" "-s" "-X" "POST" url
                  "-F" (format "file=@%s" audio-file)
                  "-F" (format "language=%s" qwen-voice-language))))
      (set-process-sentinel
       proc
       (lambda (p event)
         (when (string-match-p "finished" event)
           (with-current-buffer output-buffer
             (let ((content (buffer-string)))
               (if (string-empty-p content)
                   (message "Error ASR: respuesta vacía")
                 (condition-case err
                     (progn
                       (goto-char (point-min))
                       (let* ((json-object-type 'alist)
                              (response (json-read)))
                         (if-let ((detail (alist-get 'detail response)))
                             (message "Error ASR: %s" detail)
                           (let ((text (alist-get 'text response)))
                             (if text
                                 (funcall callback text)
                               (message "Error ASR: respuesta sin texto"))))))
                   (error
                    (message "Error ASR: %s (respuesta: %s)"
                             (error-message-string err)
                             (substring content 0 (min 100 (length content))))))))
           (kill-buffer output-buffer))))))))

;;; Comandos interactivos TTS

;;;###autoload
(defun qwen-voice-tts-region (start end)
  "Lee en voz alta el texto de la región entre START y END."
  (interactive "r")
  (let ((text (buffer-substring-no-properties start end)))
    (when (string-empty-p (string-trim text))
      (user-error "La región está vacía"))
    (qwen-voice--tts-request
     text
     (lambda (audio-file)
       (qwen-voice--play-audio
        audio-file
        (lambda ()
          ;; Solo borrar si es archivo temporal
          (unless qwen-voice-tts-output-file
            (delete-file audio-file))))))))

;;;###autoload
(defun qwen-voice-tts-buffer ()
  "Lee en voz alta todo el contenido del buffer."
  (interactive)
  (let ((text (buffer-substring-no-properties (point-min) (point-max))))
    (when (string-empty-p (string-trim text))
      (user-error "El buffer está vacío"))
    (qwen-voice--tts-request
     text
     (lambda (audio-file)
       (qwen-voice--play-audio
        audio-file
        (lambda ()
          ;; Solo borrar si es archivo temporal
          (unless qwen-voice-tts-output-file
            (delete-file audio-file))))))))

;;; Comandos interactivos ASR

;;;###autoload
(defun qwen-voice-asr-record (&optional duration)
  "Graba audio por DURATION segundos y transcribe.
El texto transcrito se inserta en el punto actual.
Con prefijo, pregunta por la duración."
  (interactive
   (list (when current-prefix-arg
           (read-number "Duración en segundos: " qwen-voice-record-duration))))
  (let ((audio-file (qwen-voice--temp-file "wav"))
        (dur (or duration qwen-voice-record-duration))
        (insert-marker (point-marker))
        (insert-buffer (current-buffer)))
    (qwen-voice--record-audio audio-file dur)
    (set-process-sentinel
     qwen-voice--recording-process
     (lambda (p event)
       (when (or (string-match-p "finished" event)
                 (string-match-p "interrupt" event))
         (message "Grabación completada")
         (run-at-time
          0.5 nil
          (lambda ()
            (if (file-exists-p audio-file)
                (qwen-voice--asr-request
                 audio-file
                 (lambda (text)
                   (message "Transcripción: %s" text)
                   (when (buffer-live-p insert-buffer)
                     (with-current-buffer insert-buffer
                       (save-excursion
                         (goto-char insert-marker)
                         (insert text))))
                   (delete-file audio-file)))
              (message "Error: archivo de audio no encontrado")))))))))

;;;###autoload
(defun qwen-voice-asr-file (audio-file)
  "Transcribe AUDIO-FILE e inserta el texto en el punto actual."
  (interactive "fArchivo de audio: ")
  (unless (file-exists-p audio-file)
    (user-error "El archivo no existe: %s" audio-file))
  (let ((insert-marker (point-marker))
        (insert-buffer (current-buffer)))
    (qwen-voice--asr-request
     (expand-file-name audio-file)
     (lambda (text)
       (message "Transcripción: %s" text)
       (when (buffer-live-p insert-buffer)
         (with-current-buffer insert-buffer
           (save-excursion
             (goto-char insert-marker)
             (insert text))))))))

;;; Comandos de utilidad

;;;###autoload
(defun qwen-voice-stop ()
  "Detiene cualquier grabación o reproducción en curso."
  (interactive)
  (qwen-voice--stop-recording)
  (when (and qwen-voice--playback-process
             (process-live-p qwen-voice--playback-process))
    (kill-process qwen-voice--playback-process)
    (setq qwen-voice--playback-process nil))
  (message "Detenido"))

;;;###autoload
(defun qwen-voice-health-check ()
  "Verifica el estado de los servidores TTS y ASR."
  (interactive)
  (let ((tts-url (concat qwen-voice-tts-url "/health"))
        (asr-url (concat qwen-voice-asr-url "/health"))
        (tts-status nil)
        (asr-status nil))
    ;; Check TTS server
    (plz 'get tts-url
      :as #'json-read
      :then (lambda (response)
              (setq tts-status (if (eq (alist-get 'tts_loaded response) t) "OK" "No cargado"))
              (message "TTS (%s): %s" qwen-voice-tts-url tts-status))
      :else (lambda (err)
              (message "TTS (%s): Error - %s" qwen-voice-tts-url (qwen-voice--format-error err))))
    ;; Check ASR server
    (plz 'get asr-url
      :as #'json-read
      :then (lambda (response)
              (setq asr-status (if (eq (alist-get 'asr_loaded response) t) "OK" "No cargado"))
              (message "ASR (%s): %s" qwen-voice-asr-url asr-status))
      :else (lambda (err)
              (message "ASR (%s): Error - %s" qwen-voice-asr-url (qwen-voice--format-error err))))))

(provide 'qwen-voice)
;;; qwen-voice.el ends here
