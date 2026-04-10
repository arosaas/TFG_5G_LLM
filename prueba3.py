# PRUEBA NUMERO TRES DEL MODELO DE GEMINI PARA EL TFG. ESTE MODELO RES
# PONDE A LAS CUESTIONES PROPORCIONADAS, SIN CONTEXTO Y SIN INFORMACION

from google import genai
import os

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()

model="gemini-2.5-flash"

def chat_terminal():
	while True:
		user_imput = input("\nTú:" )
		if user_imput.lower() == "salir":
			break
		
		response = client.models.generate_content(
            model=model,
            contents=user_imput
			)
		print(f"\nGemini: {response.text}")
		
if __name__ == "__main__":
	chat_terminal()
