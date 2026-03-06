;;; glm-ocr.el --- GLM-OCR integration via HTTP -*- lexical-binding: t; -*-

;; Copyright (C) 2026

;; Author: Codex
;; Keywords: multimedia, convenience, ocr
;; Version: 0.1.0
;; Package-Requires: ((emacs "27.1"))

;;; Commentary:

;; Este paquete proporciona integracion con el servidor GLM-OCR
;; para reconocimiento optico de caracteres (OCR) en imagenes.
;;
;; Requiere el servidor corriendo en http://localhost:8011
;; Ver: ./tools/glm-ocr/server/glm_ocr_server.py
;;
;; Comandos principales:
;; - `glm-ocr-ocr-file': Ejecuta OCR en una imagen y muestra el texto
;; - `glm-ocr-ocr-file-insert': Ejecuta OCR e inserta el texto en el punto
;; - `glm-ocr-health-check': Verifica estado del servidor

;;; Code:

(require 'json)

;;; Variables de configuracion

(defgroup glm-ocr nil
  "GLM-OCR integration via HTTP."
  :group 'external
  :prefix "glm-ocr-")

(defcustom glm-ocr-url "http://localhost:8011"
  "URL del servidor GLM-OCR."
  :type 'string
  :group 'glm-ocr)

(defcustom glm-ocr-default-mode "markdown"
  "Modo OCR por defecto (markdown o text)."
  :type '(choice (const "markdown") (const "text"))
  :group 'glm-ocr)

(defcustom glm-ocr-output-buffer "*GLM OCR*"
  "Nombre del buffer para mostrar el resultado OCR."
  :type 'string
  :group 'glm-ocr)

;;; Funciones internas

(defun glm-ocr--parse-json (string)
  "Parsea STRING como JSON y retorna un alist."
  (if (fboundp 'json-parse-string)
      (json-parse-string string :object-type 'alist)
    (let ((json-object-type 'alist))
      (json-read-from-string string))))

(defun glm-ocr--ocr-request (file mode)
  "Envia FILE al servidor OCR con MODE y retorna el resultado.
Retorna un alist con 'text, 'mode, 'prompt, etc."
  (let* ((url (concat glm-ocr-url "/ocr"))
         (stdout (generate-new-buffer " *glm-ocr-stdout*"))
         (expanded-file (expand-file-name file))
         (exit-code (call-process
                     "curl" nil stdout nil
                     "-s" "-X" "POST" url
                     "-F" (format "file=@%s" expanded-file)
                     "-F" (format "mode=%s" mode))))
    (unwind-protect
        (with-current-buffer stdout
          (let ((content (buffer-string)))
            (if (and (eq exit-code 0) (not (string-empty-p content)))
                (condition-case err
                    (let ((response (glm-ocr--parse-json content)))
                      (if (alist-get 'detail response)
                          (error "OCR error: %s" (alist-get 'detail response))
                        response))
                  (json-parse-error
                   (error "Error parseando respuesta: %s" content)))
              (error "Error curl (codigo %d): %s" exit-code content))))
      (kill-buffer stdout))))

;;; Comandos interactivos

;;;###autoload
(defun glm-ocr-ocr-file (file)
  "Ejecuta OCR en FILE y muestra el texto en un buffer."
  (interactive "fArchivo de imagen: ")
  (unless (file-exists-p file)
    (user-error "El archivo no existe: %s" file))
  (message "Procesando imagen con OCR...")
  (condition-case err
      (let* ((response (glm-ocr--ocr-request file glm-ocr-default-mode))
             (text (alist-get 'text response)))
        (with-current-buffer (get-buffer-create glm-ocr-output-buffer)
          (erase-buffer)
          (insert (or text ""))
          (goto-char (point-min))
          (pop-to-buffer (current-buffer)))
        (message "OCR completado"))
    (error
     (message "Error OCR: %s" (error-message-string err)))))

;;;###autoload
(defun glm-ocr-ocr-file-insert (file)
  "Ejecuta OCR en FILE e inserta el texto en el punto actual."
  (interactive "fArchivo de imagen: ")
  (unless (file-exists-p file)
    (user-error "El archivo no existe: %s" file))
  (message "Procesando imagen con OCR...")
  (condition-case err
      (let* ((response (glm-ocr--ocr-request file glm-ocr-default-mode))
             (text (alist-get 'text response)))
        (insert (or text ""))
        (message "OCR completado e insertado"))
    (error
     (message "Error OCR: %s" (error-message-string err)))))

;;;###autoload
(defun glm-ocr-set-mode (mode)
  "Establece el modo OCR por defecto a MODE."
  (interactive
   (list (completing-read "Modo OCR: " '("markdown" "text") nil t)))
  (setq glm-ocr-default-mode mode)
  (message "Modo OCR establecido a: %s" mode))

;;;###autoload
(defun glm-ocr-health-check ()
  "Verifica el estado del servidor OCR."
  (interactive)
  (let* ((url (concat glm-ocr-url "/health"))
         (stdout (generate-new-buffer " *glm-ocr-health*"))
         (exit-code (call-process "curl" nil stdout nil "-s" url)))
    (unwind-protect
        (with-current-buffer stdout
          (let ((content (buffer-string)))
            (if (and (eq exit-code 0) (not (string-empty-p content)))
                (condition-case nil
                    (let* ((response (glm-ocr--parse-json content))
                           (status (alist-get 'status response))
                           (loaded (alist-get 'loaded response))
                           (device (alist-get 'device response)))
                      (message "OCR Server (%s): %s, modelo %s, device: %s"
                               glm-ocr-url
                               status
                               (if loaded "cargado" "NO cargado")
                               (or device "?")))
                  (error
                   (message "OCR Server: respuesta invalida")))
              (message "OCR Server (%s): No disponible" glm-ocr-url))))
      (kill-buffer stdout))))

(provide 'glm-ocr)
;;; glm-ocr.el ends here
