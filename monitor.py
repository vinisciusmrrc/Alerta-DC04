import os
import time
import requests

# ============================================================
# CONFIGURAÇÕES
# ============================================================

URL = "https://monitoramento.defesacivil.itajai.sc.gov.br/api/v1/rios/4"

LIMITE_INICIAL = 1.65
INCREMENTO = 0.10

ARQUIVO_ESTADO = "estado.txt"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# Quantas vezes tentar novamente caso a API responda 429
MAX_TENTATIVAS = 5

# Tempo inicial de espera entre tentativas
ESPERA_INICIAL = 15


# ============================================================
# BUSCAR DADOS DO DC-04
# ============================================================

def obter_dc04():

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    for tentativa in range(1, MAX_TENTATIVAS + 1):

        try:

            print(
                f"Consultando API do DC-04 "
                f"(tentativa {tentativa}/{MAX_TENTATIVAS})..."
            )

            resposta = requests.get(
                URL,
                headers=headers,
                timeout=30
            )

            # ------------------------------------------------
            # RATE LIMIT - HTTP 429
            # ------------------------------------------------

            if resposta.status_code == 429:

                retry_after = resposta.headers.get("Retry-After")

                if retry_after:
                    try:
                        espera = int(retry_after)
                    except ValueError:
                        espera = ESPERA_INICIAL * tentativa
                else:
                    espera = ESPERA_INICIAL * tentativa

                print(
                    f"API respondeu 429 (Too Many Requests). "
                    f"Aguardando {espera} segundos..."
                )

                if tentativa < MAX_TENTATIVAS:
                    time.sleep(espera)
                    continue

                raise RuntimeError(
                    "A API continuou respondendo 429 "
                    "após várias tentativas."
                )

            # ------------------------------------------------
            # OUTROS ERROS HTTP
            # ------------------------------------------------

            resposta.raise_for_status()

            # ------------------------------------------------
            # PROCESSAR RESPOSTA
            # ------------------------------------------------

            dados = resposta.json()

            if dados.get("id") != 4:
                raise RuntimeError(
                    "A API não retornou o DC-04."
                )

            nivel_texto = dados.get("nivel_rio_m")
            medido_em = dados.get("medido_em")

            if not nivel_texto:
                raise RuntimeError(
                    "Nível do rio não encontrado na resposta da API."
                )

            # Exemplo:
            # "1,05 m" -> 1.05

            nivel = float(
                nivel_texto
                .replace("m", "")
                .replace(",", ".")
                .strip()
            )

            print("API consultada com sucesso.")

            return nivel, medido_em

        except requests.exceptions.RequestException as erro:

            if tentativa >= MAX_TENTATIVAS:
                raise RuntimeError(
                    f"Não foi possível acessar a API após "
                    f"{MAX_TENTATIVAS} tentativas: {erro}"
                )

            espera = ESPERA_INICIAL * tentativa

            print(
                f"Erro de conexão: {erro}. "
                f"Aguardando {espera} segundos..."
            )

            time.sleep(espera)


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensagem):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    resposta = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": mensagem
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

        with open(ARQUIVO_ESTADO, "r") as arquivo:
            return int(arquivo.read().strip())

    except:

        return -1


def salvar_estado(patamar):

    with open(ARQUIVO_ESTADO, "w") as arquivo:
        arquivo.write(str(patamar))


# ============================================================
# CALCULAR PATAMAR
# ============================================================

def calcular_patamar(nivel):

    # Abaixo de 1,65 m = nenhum alerta

    if nivel < LIMITE_INICIAL:
        return -1

    # Pequena tolerância para evitar problemas
    # de ponto flutuante

    return int(
        (nivel - LIMITE_INICIAL + 0.000001)
        / INCREMENTO
    )


# ============================================================
# EXECUÇÃO
# ============================================================

nivel, medido_em = obter_dc04()

patamar_atual = calcular_patamar(nivel)
patamar_anterior = carregar_estado()


print(f"DC-04: {nivel:.2f} m")
print(f"Última medição: {medido_em}")
print(f"Patamar atual: {patamar_atual}")
print(f"Patamar anterior: {patamar_anterior}")


# ============================================================
# NOVO ALERTA
# ============================================================

if patamar_atual > patamar_anterior:

    limite_atingido = (
        LIMITE_INICIAL
        + (patamar_atual * INCREMENTO)
    )

    mensagem = (
        "🚨🚨 ALERTA DC-04 🚨🚨\n\n"
        "🌊 Rio Itajaí-Mirim\n"
        "📍 Vitalmar Pescados\n\n"
        f"🌊 Nível atual: {nivel:.2f} m\n"
        f"⚠️ Limite atingido: {limite_atingido:.2f} m\n"
        f"🕐 Medição: {medido_em}\n\n"
        "⚠️ Atenção: o nível do rio atingiu "
        "um novo patamar de alerta."
    )

    enviar_telegram(mensagem)

    salvar_estado(patamar_atual)

    print("🚨 ALERTA ENVIADO PELO TELEGRAM.")


# ============================================================
# RIO ABAIXOU
# ============================================================

elif patamar_atual < patamar_anterior:

    salvar_estado(patamar_atual)

    print("Nível caiu. Estado atualizado.")


# ============================================================
# NENHUMA MUDANÇA
# ============================================================

else:

    print(
        "Nenhum novo patamar atingido. "
        "Nenhum alerta enviado."
    )