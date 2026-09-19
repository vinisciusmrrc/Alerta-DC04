import os
import re
import requests
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL = "https://defesacivil.itajai.sc.gov.br/monitoramento/nivel-rios"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

LIMITE_INICIAL = 1.20
INCREMENTO = 0.10

ARQUIVO_ESTADO = "estado.txt"


# ============================================================
# BUSCAR DADOS DO DC-04
# ============================================================

def obter_dc04():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Mobile/15E148 Safari/604.1"
        )
    }

    resposta = requests.get(
        URL,
        headers=headers,
        timeout=30
    )

    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "html.parser")

    texto = soup.get_text(" ", strip=True)

    # Normaliza espaços
    texto = re.sub(r"\s+", " ", texto)

    # Procura especificamente o DC-04
    padrao = (
        r"DC-04\s+"
        r"Rio Itajaí-Mirim.*?"
        r"Vitalmar Pescados.*?"
        r"Nível do Rio:\s*([0-9]+[,.][0-9]+)\s*m.*?"
        r"Data e hora da medição:\s*([0-9/]+)\s+([0-9:]+)"
    )

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:

        # Segunda tentativa mais simples,
        # caso a Defesa Civil altere um pouco o texto.
        padrao_fallback = (
            r"DC-04.*?"
            r"Nível do Rio:\s*([0-9]+[,.][0-9]+)\s*m.*?"
            r"Data e hora da medição:\s*([0-9/]+)\s+([0-9:]+)"
        )

        resultado = re.search(
            padrao_fallback,
            texto,
            re.IGNORECASE
        )

    if not resultado:
        raise RuntimeError(
            "Não foi possível localizar os dados do DC-04 "
            "na página da Defesa Civil."
        )

    nivel = float(
        resultado.group(1).replace(",", ".")
    )

    data = resultado.group(2)
    hora = resultado.group(3)

    return nivel, data, hora


# ============================================================
# ENVIAR MENSAGEM PELO TELEGRAM
# ============================================================

def enviar_telegram(mensagem):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem,
        },
        timeout=30
    )

    resposta.raise_for_status()


# ============================================================
# ESTADO DO MONITOR
# ============================================================

def carregar_estado():

    if not os.path.exists(ARQUIVO_ESTADO):
        return -1

    try:

        with open(
            ARQUIVO_ESTADO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return int(
                arquivo.read().strip()
            )

    except Exception:

        return -1


def salvar_estado(patamar):

    with open(
        ARQUIVO_ESTADO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        arquivo.write(str(patamar))


# ============================================================
# CALCULAR PATAMAR
# ============================================================

def calcular_patamar(nivel):

    # Abaixo de 1,65 m = nenhum alerta
    if nivel < LIMITE_INICIAL:
        return -1

    # Pequena margem para evitar erro de ponto flutuante
    return int(
        (nivel - LIMITE_INICIAL + 0.000001)
        / INCREMENTO
    )


# ============================================================
# EXECUÇÃO
# ============================================================

try:

    nivel, data, hora = obter_dc04()

    patamar_atual = calcular_patamar(nivel)

    patamar_anterior = carregar_estado()

    print(
        f"DC-04: {nivel:.2f} m | "
        f"Medição: {data} {hora} | "
        f"Patamar atual: {patamar_atual} | "
        f"Patamar anterior: {patamar_anterior}"
    )

    # --------------------------------------------------------
    # SUBIU PARA UM NOVO PATAMAR
    # --------------------------------------------------------

    if patamar_atual > patamar_anterior:

        limite_atingido = (
            LIMITE_INICIAL
            + (patamar_atual * INCREMENTO)
        )

        mensagem = (
            "🚨🚨 ALERTA DC-04 🚨🚨\n\n"
            f"🌊 Nível atual: {nivel:.2f} m\n"
            f"📍 Vitalmar Pescados\n"
            f"🕐 Medição: {data} {hora}\n\n"
            f"⚠️ Limite atingido: "
            f"{limite_atingido:.2f} m"
        )

        enviar_telegram(mensagem)

        salvar_estado(patamar_atual)

        print(
            f"ALERTA ENVIADO: "
            f"{limite_atingido:.2f} m"
        )

    # --------------------------------------------------------
    # NÍVEL CAIU ABAIXO DO LIMITE
    # --------------------------------------------------------

    elif patamar_atual < patamar_anterior:

        salvar_estado(patamar_atual)

        print(
            "Nível caiu. Estado atualizado."
        )

    # --------------------------------------------------------
    # MESMO PATAMAR
    # --------------------------------------------------------

    else:

        print(
            "Nenhum novo alerta necessário."
        )


except Exception as erro:

    print(
        "ERRO NO MONITORAMENTO:"
    )

    print(
        str(erro)
    )

    raise
