import cv2

def find_available_cameras():
    """
    Busca en los índices de cámara para encontrar las que están disponibles.
    """
    print("--- Buscando camaras disponibles ---")
    max_cameras_to_check = 10
    available_cameras = []
    
    for i in range(max_cameras_to_check):
        # Intenta abrir la cámara con la API DSHOW, que es la más compatible
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        
        if cap is not None and cap.isOpened():
            print(f"Indice {i}: Camara encontrada y abierta con exito.")
            # Intenta leer un frame para confirmar que es una fuente de video válida
            ret, frame = cap.read()
            if ret:
                print(f"Indice {i}: ¡Lectura de frame exitosa! Esta camara funciona.")
                available_cameras.append(i)
            else:
                print(f"Indice {i}: Se pudo abrir, pero no se pudo leer un frame. (Posiblemente en uso o invalida)")
            
            cap.release()
        else:
            print(f"Indice {i}: No se encontro ninguna camara.")
            
    return available_cameras

if __name__ == "__main__":
    cameras = find_available_cameras()
    if cameras:
        print(f"\n--- Resumen ---")
        print(f"Se encontraron las siguientes camaras funcionales: {cameras}")
        print(f"El indice mas probable para DroidCam (o una camara externa) es el numero mas alto: {max(cameras)}")
    else:
        print("\nNo se encontro ninguna camara funcional compatible con OpenCV.")
