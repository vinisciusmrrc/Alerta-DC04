import re
import requests
from bs4 import BeautifulSoup

URL = "https://defesacivil.itajai.sc.gov.br/monitoramento/nivel-rios"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

print("========================================")
print("DIAGNOSTICO DO NOVO SITE")
print("========================================")

resposta = requests.get(
    URL,
    headers=headers,
    timeout=30
)

resposta.raise_for_status()

print("STATUS:", resposta.status_code)
print("URL:", resposta.url)
print("HTML:", len(resposta.text), "bytes")

soup = BeautifulSoup(
    resposta.text,
    "html.parser"
)

script = soup.find(
    "script",
    src=True
)

if not script:
    raise RuntimeError(
        "Não encontrei o arquivo JavaScript principal."
    )

js_src = script["src"]

if js_src.startswith("/"):
    js_url = "https://defesacivil.itajai.sc.gov.br" + js_src
else:
    js_url = js_src

print()
print("JAVASCRIPT PRINCIPAL:")
print(js_url)

js = requests.get(
    js_url,
    headers=headers,
    timeout=30
)

js.raise_for_status()

print("TAMANHO DO JAVASCRIPT:", len(js.text), "bytes")

texto = js.text

print()
print("========================================")
print("TERMOS RELACIONADOS A API")
print("========================================")

padroes = [
    r'["\']([^"\']*api[^"\']*)["\']',
    r'["\']([^"\']*rio[^"\']*)["\']',
    r'["\']([^"\']*nivel[^"\']*)["\']',
    r'["\']([^"\']*monitoramento[^"\']*)["\']',
]

encontrados = set()

for padrao in padroes:
    resultados = re.findall(
        padrao,
        texto,
        re.IGNORECASE
    )

    for resultado in resultados:
        if len(resultado) < 300:
            encontrados.add(resultado)

for item in sorted(encontrados):
    print(item)

print()
print("========================================")
print("URLS ENCONTRADAS")
print("========================================")

urls = re.findall(
    r'https?://[^"\']+',
    texto
)

for url in sorted(set(urls)):
    print(url[:500])

print()
print("========================================")
print("TRECHOS COM fetch / axios")
print("========================================")

for termo in [
    "fetch(",
    "axios",
    ".get(",
    "/api/",
    "DC-04",
    "nivel-rios"
]:
    print()
    print("-----", termo, "-----")

    posicoes = []
    inicio = 0

    while True:
        pos = texto.lower().find(
            termo.lower(),
            inicio
        )

        if pos == -1:
            break

        posicoes.append(pos)
        inicio = pos + len(termo)

    for pos in posicoes[:10]:
        inicio_trecho = max(0, pos - 300)
        fim_trecho = min(
            len(texto),
            pos + 500
        )

        print(
            texto[inicio_trecho:fim_trecho]
        )
        print()