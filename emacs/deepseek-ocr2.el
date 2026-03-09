;;; deepseek-ocr2.el --- DeepSeek OCR 2 integration via HTTP -*- lexical-binding: t; -*-

;; Copyright (C) 2026

;; Author: Claude
;; Keywords: multimedia, convenience, ocr
;; Version: 2.0.0
;; Package-Requires: ((emacs "27.1"))

;;; Commentary:

;; Este paquete proporciona integración con el servidor DeepSeek OCR 2
;; para reconocimiento óptico de caracteres (OCR) en imágenes.
;;
;; Requiere el servidor corriendo en http://localhost:8010
<<<<<<< HEAD
;; Ver: ./tools/deepseek-ocr2/server/deepseek_ocr2_server.py
=======
;; Ver: apps/ocr_deepseek_api/main.py
>>>>>>> de70b7b (remove nix in favor python uv, clean the project and reduce redundancy)
;;
;; Comandos principales:
;; - `deepseek-ocr2-ocr-file': Ejecuta OCR en una imagen y muestra el texto
;; - `deepseek-ocr2-ocr-file-insert': Ejecuta OCR e inserta el texto en el punto
;; - `deepseek-ocr2-health-check': Verifica estado del servidor

;;; Code:

(require 'json)

;;; Variables de configuración

(defgroup deepseek-ocr2 nil
  "DeepSeek OCR 2 integration via HTTP."
  :group 'external
  :prefix "deepseek-ocr2-")

(defcustom deepseek-ocr2-url "http://localhost:8010"
  "URL del servidor DeepSeek OCR 2."
  :type 'string
  :group 'deepseek-ocr2)

(defcustom deepseek-ocr2-default-mode "markdown"
  "Modo OCR por defecto (markdown o text)."
  :type '(choice (const "markdown") (const "text"))
  :group 'deepseek-ocr2)

(defcustom deepseek-ocr2-output-buffer "*DeepSeek OCR2*"
  "Nombre del buffer para mostrar el resultado OCR."
  :type 'string
  :group 'deepseek-ocr2)

;;; Funciones internas

(defun deepseek-ocr2--parse-json (string)
  "Parsea STRING como JSON y retorna un alist."
  (if (fboundp 'json-parse-string)
      (json-parse-string string :object-type 'alist)
    (let ((json-object-type 'alist))
      (json-read-from-string string))))

(defun deepseek-ocr2--ocr-request (file mode)
  "Envía FILE al servidor OCR con MODE y retorna el resultado.
Retorna un alist con 'text, 'mode, 'prompt, etc."
  (let* ((url (concat deepseek-ocr2-url "/ocr"))
         (stdout (generate-new-buffer " *deepseek-ocr2-stdout*"))
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
                    (let ((response (deepseek-ocr2--parse-json content)))
                      (if (alist-get 'detail response)
                          (error "OCR error: %s" (alist-get 'detail response))
                        response))
                  (json-parse-error
                   (error "Error parseando respuesta: %s" content)))
              (error "Error curl (código %d): %s" exit-code content))))
      (kill-buffer stdout))))

;;; Comandos interactivos

;;;###autoload
(defun deepseek-ocr2-ocr-file (file)
  "Ejecuta OCR en FILE y muestra el texto en un buffer."
  (interactive "fArchivo de imagen: ")
  (unless (file-exists-p file)
    (user-error "El archivo no existe: %s" file))
  (message "Procesando imagen con OCR...")
  (condition-case err
      (let* ((response (deepseek-ocr2--ocr-request file deepseek-ocr2-default-mode))
             (text (alist-get 'text response)))
        (with-current-buffer (get-buffer-create deepseek-ocr2-output-buffer)
          (erase-buffer)
          (insert (or text ""))
          (goto-char (point-min))
          (pop-to-buffer (current-buffer)))
        (message "OCR completado"))
    (error
     (message "Error OCR: %s" (error-message-string err)))))

;;;###autoload
(defun deepseek-ocr2-ocr-file-insert (file)
  "Ejecuta OCR en FILE e inserta el texto en el punto actual."
  (interactive "fArchivo de imagen: ")
  (unless (file-exists-p file)
    (user-error "El archivo no existe: %s" file))
  (message "Procesando imagen con OCR...")
  (condition-case err
      (let* ((response (deepseek-ocr2--ocr-request file deepseek-ocr2-default-mode))
             (text (alist-get 'text response)))
        (insert (or text ""))
        (message "OCR completado e insertado"))
    (error
     (message "Error OCR: %s" (error-message-string err)))))

;;;###autoload
(defun deepseek-ocr2-set-mode (mode)
  "Establece el modo OCR por defecto a MODE."
  (interactive
   (list (completing-read "Modo OCR: " '("markdown" "text") nil t)))
  (setq deepseek-ocr2-default-mode mode)
  (message "Modo OCR establecido a: %s" mode))

;;;###autoload
(defun deepseek-ocr2-health-check ()
  "Verifica el estado del servidor OCR."
  (interactive)
  (let* ((url (concat deepseek-ocr2-url "/health"))
         (stdout (generate-new-buffer " *deepseek-ocr2-health*"))
         (exit-code (call-process "curl" nil stdout nil "-s" url)))
    (unwind-protect
        (with-current-buffer stdout
          (let ((content (buffer-string)))
            (if (and (eq exit-code 0) (not (string-empty-p content)))
                (condition-case nil
                    (let* ((response (deepseek-ocr2--parse-json content))
                           (status (alist-get 'status response))
                           (loaded (alist-get 'loaded response))
                           (device (alist-get 'device response)))
                      (message "OCR Server (%s): %s, modelo %s, device: %s"
                               deepseek-ocr2-url
                               status
                               (if loaded "cargado" "NO cargado")
                               (or device "?")))
                  (error
                   (message "OCR Server: respuesta inválida")))
              (message "OCR Server (%s): No disponible" deepseek-ocr2-url))))
      (kill-buffer stdout))))

(provide 'deepseek-ocr2)
;;; deepseek-ocr2.el ends here
