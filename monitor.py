import json
import requests

URL = "https://monitoramento.defesacivil.itajai.sc.gov.br/api/v1/rios"

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

print("\n===== RESPOSTA COMPLETA DA API =====")
print(json.dumps(dados, ensure_ascii=False, indent=2))
print("====================================")