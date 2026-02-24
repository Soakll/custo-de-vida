from flask import Flask, render_template, request, jsonify
import plotly.graph_objects as go
import plotly.utils
import json

from services.ibge_service import (
    buscar_cidades_por_orcamento,
    buscar_custo_estimado,
    listar_cidades,
)
from services.crime_service import (
    buscar_crimes_por_uf,
    buscar_crimes_por_capital,
)

app = Flask(__name__)

LAYOUT_BASE = {
    "template":      "plotly_white",
    "title_x":       0.5,
    "title_xanchor": "center",
}


def _parsear_params(req):
    try:
        orcamento = float(req.args.get("orcamento", 0))
        pessoas   = int(req.args.get("pessoas", 1))
    except ValueError:
        raise ValueError("Valores inválidos para orçamento ou pessoas.")
    if orcamento <= 0:
        raise ValueError("Informe um orçamento maior que zero.")
    return orcamento, pessoas


@app.route("/")
def index():
    return render_template("index.html", cidades=listar_cidades())


@app.route("/api/consultar")
def api_consultar():
    try:
        orcamento, pessoas = _parsear_params(request)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400

    resultados = buscar_cidades_por_orcamento(orcamento, pessoas)
    if not resultados:
        return jsonify({"erro": "Não foi possível calcular os dados. Tente novamente."}), 503

    grafico = _gerar_grafico_comparacao(resultados, orcamento)
    return jsonify({
        "cidades": resultados,
        "grafico": json.dumps(grafico, cls=plotly.utils.PlotlyJSONEncoder),
    })


@app.route("/api/grafico/detalhes")
def api_grafico_detalhes():
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
        **LAYOUT_BASE,
    )
    return jsonify({"grafico": json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)})


@app.route("/api/crime/uf")
def api_crime_uf():
    dados = buscar_crimes_por_uf()
    if "erro" in dados:
        return jsonify(dados), 503

    estados     = dados["estados"]
    tipos       = dados["tipos"]
    tipo_filtro = request.args.get("tipo", "todos")

    if tipo_filtro != "todos" and tipo_filtro in tipos:
        ranking = sorted(
            [{"uf": uf, "total": v["crimes"].get(tipo_filtro, 0), "crimes": v["crimes"]}
             for uf, v in estados.items()],
            key=lambda x: x["total"]
        )
    else:
        ranking = sorted(
            [{"uf": uf, "total": v["total"], "crimes": v["crimes"]}
             for uf, v in estados.items()],
            key=lambda x: x["total"]
        )

    fig = go.Figure(go.Bar(
        x=[r["uf"]    for r in ranking],
        y=[r["total"] for r in ranking],
        marker_color="#3498db",
        hovertemplate="<b>%{x}</b><br>Ocorrências: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Ocorrências criminais por estado — {dados['ano']}" +
              (f"<br><sup>{tipo_filtro}</sup>" if tipo_filtro != "todos" else ""),
        xaxis_title="Estado", yaxis_title="Ocorrências",
        showlegend=False, xaxis_tickangle=-30, **LAYOUT_BASE,
    )

    return jsonify({
        "ano":     dados["ano"],
        "tipos":   tipos,
        "ranking": ranking,
        "grafico": json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
    })


@app.route("/api/crime/capitais")
def api_crime_capitais():
    dados = buscar_crimes_por_capital()
    if "erro" in dados:
        return jsonify(dados), 503

    capitais    = dados["capitais"]
    tipos       = dados["tipos"]
    tipo_filtro = request.args.get("tipo", "todos")

    if tipo_filtro != "todos" and tipo_filtro in tipos:
        ranking = sorted(
            [{"cidade": c, "estado": v["estado"], "total": v["crimes"].get(tipo_filtro, 0), "crimes": v["crimes"]}
             for c, v in capitais.items()],
            key=lambda x: x["total"]
        )
    else:
        ranking = sorted(
            [{"cidade": c, "estado": v["estado"], "total": v["total"], "crimes": v["crimes"]}
             for c, v in capitais.items()],
            key=lambda x: x["total"]
        )

    fig = go.Figure(go.Bar(
        x=[r["cidade"] for r in ranking],
        y=[r["total"]  for r in ranking],
        marker_color="#9b59b6",
        hovertemplate="<b>%{x}</b><br>Ocorrências: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Ocorrências criminais por capital — {dados['ano']}" +
              (f"<br><sup>{tipo_filtro}</sup>" if tipo_filtro != "todos" else ""),
        xaxis_title="Capital", yaxis_title="Ocorrências",
        showlegend=False, xaxis_tickangle=-30, **LAYOUT_BASE,
    )

    return jsonify({
        "ano":     dados["ano"],
        "tipos":   tipos,
        "ranking": ranking,
        "grafico": json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder),
    })


def _gerar_grafico_comparacao(resultados: list, orcamento: float) -> go.Figure:
    cidades = [r["cidade"] for r in resultados]
    totais  = [r["total"]  for r in resultados]
    cores   = ["#2ecc71" if r["cabe_no_orcamento"] else "#e74c3c" for r in resultados]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cidades, y=totais, marker_color=cores,
        hovertemplate="<b>%{x}</b><br>Custo estimado: R$ %{y:,.0f}/mês<extra></extra>",
    ))
    fig.add_hline(
        y=orcamento, line_dash="dash", line_color="#2c3e50",
        annotation_text=f"Seu orçamento: R$ {orcamento:,.0f}",
        annotation_position="top right",
    )
    fig.update_layout(
        title="Custo de vida estimado por cidade",
        xaxis_title="Cidade", yaxis_title="Custo mensal (R$)",
        showlegend=False, xaxis_tickangle=-30, **LAYOUT_BASE,
    )
    return fig


if __name__ == "__main__":
    app.run(debug=True)