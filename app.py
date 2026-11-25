# -*- coding: utf-8 -*-
import re
import unicodedata

from flask import Flask, jsonify, render_template, request, send_file
from io import BytesIO

from cv_pdf import gerar_pdf
from schema import ErroValidacao, validar

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024  # o JSON do formulario nunca chega perto disso


def nome_arquivo(nome):
    ascii_ = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    partes = re.sub(r"[^A-Za-z0-9 ]", "", ascii_).split()
    return "CV_" + ("_".join(partes[:4]) or "Curriculo") + ".pdf"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/gerar")
def gerar():
    dados = request.get_json(silent=True)
    try:
        cv = validar(dados)
    except ErroValidacao as erro:
        return jsonify(erro=str(erro)), 400

    try:
        pdf = gerar_pdf(cv)
    except Exception:
        app.logger.exception("Falha ao gerar PDF")
        return jsonify(erro="Não foi possível gerar o PDF. Revise os dados e tente novamente."), 500

    return send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nome_arquivo(cv["pessoal"]["nome"]),
    )


@app.errorhandler(413)
def muito_grande(_):
    return jsonify(erro="Conteúdo grande demais. Reduza os textos e tente novamente."), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
