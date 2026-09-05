import os
import re
import requests
from bs4 import BeautifulSoup

URL = "https://defesacivil.itajai.sc.gov.br/monitoramento/nivel-rios"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LIMITE_INICIAL = 1.65
INCREMENTO = 0.10
ARQUIVO_ESTADO = "estado.txt"


def obter_dc04():
    resposta = requests.get(URL, timeout=30)
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")
    texto = soup.get_text(" ", strip=True)

    padrao = (
        r"DC-04.*?"
        r"Nível do Rio:\s*([0-9]+,[0-9]+)\s*m.*?"
        r"Data e hora da medição:\s*([0-9/]+)\s+([0-9:]+)"
    )

    resultado = re.search(padrao, texto)

    if not resultado:
        raise RuntimeError("Não foi possível encontrar o DC-04 na página.")

    nivel = float(resultado.group(1).replace(",", "."))
    data = resultado.group(2)
    hora = resultado.group(3)

    return nivel, data, hora


def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem,
        },
        timeout=30,
    )

    resposta.raise_for_status()


def carregar_estado():
    if not os.path.exists(ARQUIVO_ESTADO):
        return -1

    with open(ARQUIVO_ESTADO, "r") as arquivo:
        return int(arquivo.read().strip())


def salvar_estado(patamar):
    with open(ARQUIVO_ESTADO, "w") as arquivo:
        arquivo.write(str(patamar))


def calcular_patamar(nivel):
    if nivel < LIMITE_INICIAL:
        return -1

    return int((nivel - LIMITE_INICIAL + 0.000001) / INCREMENTO)


nivel, data, hora = obter_dc04()

patamar_atual = calcular_patamar(nivel)
patamar_anterior = carregar_estado()


if patamar_atual > patamar_anterior:

    limite_atingido = LIMITE_INICIAL + (patamar_atual * INCREMENTO)

    mensagem = (
        "🚨🚨 ALERTA DC-04 🚨🚨\n\n"
        f"🌊 Nível atual: {nivel:.2f} m\n"
        f"📍 Vitalmar Pescados\n"
        f"🕐 Medição: {data} {hora}\n\n"
        f"⚠️ Limite atingido: {limite_atingido:.2f} m"
    )

    enviar_telegram(mensagem)

    salvar_estado(patamar_atual)

elif patamar_atual < patamar_anterior:
    salvar_estado(patamar_atual)

print(f"DC-04: {nivel:.2f} m | Medição: {data} {hora}")
