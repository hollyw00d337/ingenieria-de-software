import cv2
import numpy as np
import requests
import base64
from PIL import Image
import io
import re

class PlateRecognitionService:
    def __init__(self):
        # Configuración para API externa
        self.api_key = "9e9914df200fabb230ba871ef0954f80f7353edd"
        self.api_url = "https://api.platerecognizer.com/v1/plate-reader/"
        self.confidence_threshold = 0.9
    
    def recognize_plate(self, image_path):
        """
        Reconoce placa vehicular desde imagen
        Retorna: {
            'success': bool,
            'plate_number': str,
            'confidence': float,
            'error': str
        }
        """
        try:
            # Método 1: Usar API externa 
            if self.api_key != "YOUR_API_KEY_HERE":
                return self._recognize_with_api(image_path)
            
            # Método 2: Procesamiento local con OpenCV 
            return self._recognize_with_opencv(image_path)
            
        except Exception as e:
            return {
                'success': False,
                'plate_number': None,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _recognize_with_api(self, image_path):
        """Reconocimiento usando API externa"""
        try:
            with open(image_path, 'rb') as image_file:
                files = {'upload': image_file}
                headers = {'Authorization': f'Token {self.api_key}'}
                
                response = requests.post(
                    self.api_url,
                    files=files,
                    headers=headers,
                    timeout=20 # Aumentado a 20 segundos
                )
                
                # Aceptamos 200 (OK) y 201 (Created) como respuestas válidas
                if response.status_code in [200, 201]:
                    data = response.json()
                    
                    if data.get('results'):
                        result = data['results'][0]
                        plate_number = result['plate'].upper()
                        confidence = result['score']
                        
                        # Validar formato de placa mexicana
                        if self._validate_mexican_plate(plate_number):
                            return {
                                'success': True,
                                'plate_number': plate_number,
                                'confidence': confidence,
                                'error': None
                            }
                    
                    return {
                        'success': False,
                        'plate_number': None,
                        'confidence': 0.0,
                        'error': 'No se detectó placa válida en la respuesta de la API.'
                    }
                else:
                    return {
                        'success': False,
                        'plate_number': None,
                        'confidence': 0.0,
                        'error': f'Error de la API. Código de estado: {response.status_code}'
                    }
        
        except Exception as e:
            return {
                'success': False,
                'plate_number': None,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _recognize_with_opencv(self, image_path):
        """Reconocimiento básico con OpenCV (para desarrollo/testing)"""
        try:
            # Cargar imagen
            image = cv2.imread(image_path)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Aplicar filtros para mejorar detección
            gray = cv2.bilateralFilter(gray, 11, 17, 17)
            edged = cv2.Canny(gray, 30, 200)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
            
            # Buscar contorno rectangular (posible placa)
            plate_contour = None
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.018 * peri, True)
                
                if len(approx) == 4:
                    plate_contour = approx
                    break
            
            if plate_contour is not None:
                # Extraer región de la placa
                mask = np.zeros(gray.shape, np.uint8)
                cv2.drawContours(mask, [plate_contour], 0, 255, -1)
                
                x, y, w, h = cv2.boundingRect(plate_contour)
                plate_region = gray[y:y+h, x:x+w]
                
                # Aquí integrarías un OCR como Tesseract
                # Por ahora retornamos un placeholder
                return {
                    'success': True,
                    'plate_number': 'ABC-123-D',  # Placeholder
                    'confidence': 0.85,
                    'error': None
                }
            
            return {
                'success': False,
                'plate_number': None,
                'confidence': 0.0,
                'error': 'No se detectó placa en la imagen'
            }
            
        except Exception as e:
            return {
                'success': False,
                'plate_number': None,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _validate_mexican_plate(self, plate):
        """Valida formato de placa mexicana"""
        # Formatos comunes: ABC-12-34, ABC-123-D, 123-ABC-4
        patterns = [
            r'^[A-Z]{3}-\d{2}-\d{2}$',  # ABC-12-34
            r'^[A-Z]{3}-\d{3}-[A-Z]$',  # ABC-123-D
            r'^\d{3}-[A-Z]{3}-\d$',     # 123-ABC-4
            r'^[A-Z]{3}\d{4}$',         # ABC1234
        ]
        
        for pattern in patterns:
            if re.match(pattern, plate):
                return True
        
        return False
    
    def test_recognition(self, image_path):
        """Método para testing manual"""
        result = self.recognize_plate(image_path)
        print(f"Resultado: {result}")
        return result
