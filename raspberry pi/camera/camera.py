# receive image
import socket

# predict image
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img
from tensorflow.keras.models import load_model

# recognize date
import pytesseract
from PIL import Image
import cv2
import re

# Create a TCP/IP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the address and port
server_socket.bind(("172.20.10.7", 8080))  # Replace with Raspberry Pi's IP address
print("Server is running on port 8080")
server_socket.listen(5)

def receive_image():
    # Wait for a connection
    client_socket, _ = server_socket.accept()

    # Receive the image size
    img_size_bytes = b''
    while len(img_size_bytes) < 4:
        chunk = client_socket.recv(4 - len(img_size_bytes))
        if not chunk:
            break
        img_size_bytes += chunk

    # Convert image size bytes to integer
    img_size = int.from_bytes(img_size_bytes, byteorder='big')

    # Receive the image data
    img_data = b''
    while len(img_data) < img_size:
        chunk = client_socket.recv(min(4096, img_size - len(img_data)))
        if not chunk:
            break
        img_data += chunk

    # Write image data to file
    with open('received_image.jpg', 'wb') as f:
        f.write(img_data)
        f.close()

    # Close the client socket
    client_socket.close()

def recognize_image():
    def predict_image(model, image_path, image_height, image_width):
        img = load_img(image_path, target_size=(image_height, image_width))
        img = img_to_array(img)
        img = np.expand_dims(img, axis=0)/255
        prediction = model.predict(img)
        return prediction

    def get_class_label(prediction, class_indices):
        class_label = None
        max_prob = np.max(prediction)
        for label, index in class_indices.items():
            if prediction[0][index] == max_prob:
                class_label = label
                break
        return class_label

    # load the model
    model = load_model('recognizer.h5')

    # create data generator for training set
    train_datagen = ImageDataGenerator(rescale=1./255)
    train_generator = train_datagen.flow_from_directory(
        "./dataset",
        target_size=(320, 240),
        batch_size=32,
        class_mode='categorical')

    # obtain class indices from the training set
    class_indices = train_generator.class_indices

    # predict the image
    image_path = './received_image.jpg'

    prediction = predict_image(model, image_path, 320, 240)
    class_label = get_class_label(prediction, class_indices)

    print(f'A imagem {image_path} é da classe {class_label} com probabilidade {np.max(prediction) * 100 :.2f}')
    if np.max(prediction) > 0.7:
        print("Produto reconhecido")
    else:
        print("Produto não reconhecido")
        class_label = "Desconhecido"
    return class_label

def recognize_date():
    padrao_data = '^(0[1-9]|[12][0-9]|3[01])/(0[1-9]|1[0-2])/[0-9]{4}$'

    image = Image.open('received_image.jpg')

    result = pytesseract.image_to_string(image)

    print(result)

    # filter date
    result = result.split(' ')
    for i in result:
        if re.match(padrao_data, i):
            print(i)
            return i
    return "Undetectable"
    
def save_last_product(product, quantity, expiration_date):
    with open('../last_product.txt', 'w') as f:
        f.write(product + '\n')
        f.write(quantity + '\n')
        f.write(expiration_date + '\n')
        f.close()

while True:
    receive_image()
    print("Image received")

    product = recognize_image()

    expiration_date = recognize_date()

    save_last_product(product, "1", expiration_date)
