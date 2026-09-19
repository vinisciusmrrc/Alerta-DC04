import json
import requests

URL = "https://monitoramento.defesacivil.itajai.sc.gov.br/api/v1/rios"

def procurar_dc04(obj):
    if isinstance(obj, dict):
        if obj.get("id") == "DC-04" or obj.get("apiId") == 4:
            return obj

        for valor in obj.values():
            resultado = procurar_dc04(valor)
            if resultado is not None:
                return resultado

    elif isinstance(obj, list):
        for item in obj:
            resultado = procurar_dc04(item)
            if resultado is not None:
                return resultado

    return None


headers = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0"
}

resposta = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("STATUS:", resposta.status_code)
print("CONTENT-TYPE:", resposta.headers.get("content-type"))
print("TAMANHO:", len(resposta.text))

resposta.raise_for_status()

dados = resposta.json()

print("TIPO DA RESPOSTA:", type(dados).__name__)

dc04 = procurar_dc04(dados)

if dc04 is None:
    print("DC-04 NÃO ENCONTRADO NA RESPOSTA DA API.")
else:
    print("\n===== DC-04 ENCONTRADO =====")
    print(json.dumps(dc04, ensure_ascii=False, indent=2))
    print("============================")