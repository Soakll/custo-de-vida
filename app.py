# app.py
# Servidor web principal — define as rotas da aplicação

from flask import Flask, render_template, request, jsonify
import plotly.graph_objects as go
import plotly.utils
import json

from services.ibge_service import (
    buscar_cidades_por_orcamento,
    buscar_custo_estimado,
    listar_cidades,
)

app = Flask(__name__)


# ─────────────────────────────────────────────────────────────
# ROTAS
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Página principal."""
    return render_template("index.html", cidades=listar_cidades())


@app.route("/api/consultar")
def api_consultar():
    """
    Retorna cidades ordenadas por custo, indicando se cabem no orçamento.

    Parâmetros na URL:
      - orcamento: valor mensal em R$ (obrigatório)
      - pessoas:   número de pessoas (padrão: 1)
    """
    try:
        orcamento = float(request.args.get("orcamento", 0))
        pessoas   = int(request.args.get("pessoas", 1))
    except ValueError:
        return jsonify({"erro": "Valores inválidos para orçamento ou pessoas."}), 400

    if orcamento <= 0:
        return jsonify({"erro": "Informe um orçamento maior que zero."}), 400

    resultados = buscar_cidades_por_orcamento(orcamento, pessoas)

    if not resultados:
        return jsonify({"erro": "Não foi possível calcular os dados. Tente novamente."}), 503

    return jsonify(resultados)


@app.route("/api/grafico/comparacao")
def api_grafico_comparacao():
    """
    Gráfico de barras comparando o custo total entre cidades,
    com linha indicando o orçamento do usuário.
    """
    try:
        orcamento = float(request.args.get("orcamento", 0))
        pessoas   = int(request.args.get("pessoas", 1))
    except ValueError:
        return jsonify({"erro": "Valores inválidos."}), 400

    resultados = buscar_cidades_por_orcamento(orcamento, pessoas)

    if not resultados:
        return jsonify({"erro": "Dados indisponíveis."}), 503

    cidades = [r["cidade"] for r in resultados]
    totais  = [r["total"]  for r in resultados]
    cores   = ["#2ecc71" if r["cabe_no_orcamento"] else "#e74c3c" for r in resultados]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=cidades,
        y=totais,
        marker_color=cores,
        hovertemplate="<b>%{x}</b><br>Custo estimado: R$ %{y:,.0f}/mês<extra></extra>",
    ))

    fig.add_hline(
        y=orcamento,
        line_dash="dash",
        line_color="#2c3e50",
        annotation_text=f"Seu orçamento: R$ {orcamento:,.0f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Custo de vida estimado por cidade",
        title_x=0.5,
        title_xanchor="center",
        xaxis_title="Cidade",
        yaxis_title="Custo mensal (R$)",
        template="plotly_white",
        showlegend=False,
        xaxis_tickangle=-30,
    )

    return jsonify({"grafico": json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)})


@app.route("/api/grafico/detalhes")
def api_grafico_detalhes():
    """
    Gráfico de rosca com distribuição de gastos por categoria para uma cidade.
    """
    cidade  = request.args.get("cidade", "São Paulo")
    pessoas = int(request.args.get("pessoas", 1))

    try:
        dados = buscar_custo_estimado(cidade, pessoas)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    fig = go.Figure(go.Pie(
        labels=list(dados["categorias"].keys()),
        values=list(dados["categorias"].values()),
        hole=0.4,
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}/mês<br>%{percent}<extra></extra>",
    ))

    fig.update_layout(
        title=(
            f"Distribuição de gastos — {cidade}<br>"
            f"<sup>Total estimado: R$ {dados['total']:,.0f}/mês · Ref: {dados['referencia']}</sup>"
        ),
        title_x=0.5,
        title_xanchor="center",
        template="plotly_white",
    )

    return jsonify({"grafico": json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)})


# ─────────────────────────────────────────────────────────────
# PONTO DE ENTRADA
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)