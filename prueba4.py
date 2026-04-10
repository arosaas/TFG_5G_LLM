# PRUEBA NUMERO TRES DEL MODELO DE GEMINI PARA EL PROYECTO. ESTE MODELO RES
# PONDE A LAS CUESTIONES PROPORCIONADAS, CON ROLE PROMPTING

from google import genai
from google.genai import types
import os

# The client gets the API key from the environment variable `GEMINI_API_KEY`.
client = genai.Client()
model="gemini-2.5-flash"

def chat_terminal():
	configuration_rol=types.GenerateContentConfig(
			system_instruction="Asume el rol de experto en configuración de redes 4G y 5G O-Ran, eres un experto en configuración de distintos escenarios como el de una LAN Party o una empresa de telefonía, emplearás tecnologías como srsRAN y OpenAir Interface"
			)
	while True:
		user_imput = input("\nTú:" )
		if user_imput.lower() == "salir":
			break
		
		response = client.models.generate_content(
            model=model,
            contents=user_imput,
            config=configuration_rol
        )
		print(f"\nGemini: {response.text}")
		
if __name__ == "__main__":
	chat_terminal()
