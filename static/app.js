(() => {
  const CHAVE = "gerador_cv_v3";
  const CHAVE_ANTIGA = "gerador_cv_v2"; // rascunho com periodo em texto livre
  const SECOES = ["habilidades", "experiencias", "formacoes", "palestras", "publicacoes", "certificacoes", "voluntariado"];
  const INICIAIS = ["habilidades", "experiencias", "formacoes"]; // abrem com 1 item vazio
  const ROTULOS = {
    habilidades: "Categoria", experiencias: "Experiência", formacoes: "Formação", palestras: "Palestra",
    publicacoes: "Publicação", certificacoes: "Certificação", voluntariado: "Voluntariado",
  };

  const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  const NOMES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                 "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
  const ANO_DO_MES = { inicio_mes: "inicio_ano", fim_mes: "fim_ano", mes: "ano" };
  const RX_ATUAL = /atual|current|present|hoje|andamento|momento/i;

  const form = document.getElementById("form");
  const status = document.getElementById("status");
  const btnGerar = document.getElementById("gerar");
  const lista = (secao) => form.querySelector(`.lista[data-secao="${secao}"]`);

  function setStatus(texto, tipo = "") {
    status.textContent = texto;
    status.className = tipo;
  }

  function renumerar(secao) {
    const itens = [...lista(secao).children];
    itens.forEach((item, i) => {
      item.querySelector(".item-num").textContent = `${ROTULOS[secao]} ${i + 1}`;
      item.querySelector(".sobe").disabled = i === 0;
      item.querySelector(".desce").disabled = i === itens.length - 1;
    });
  }

  function botao(classe, texto, titulo) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = classe;
    b.textContent = texto;
    b.title = titulo;
    b.setAttribute("aria-label", titulo);
    return b;
  }

  // --- datas -------------------------------------------------------------------
  function mesesNoSelect(sel) {
    sel.append(new Option("—", ""));
    MESES.forEach((abrev, i) => sel.append(new Option(NOMES[i], abrev)));
  }

  function normalizaMes(texto) {
    const t = texto.trim().toLowerCase().replace("ç", "c");
    if (/^\d{1,2}$/.test(t)) return MESES[+t - 1] || "";
    const i = NOMES.findIndex((nome) => {
      const n = nome.toLowerCase().replace("ç", "c");
      return t === n || t === n.slice(0, 3);
    });
    return i < 0 ? "" : MESES[i];
  }

  /** "Fev 2025", "02/2025" ou "2025" -> { mes, ano } */
  function parteData(texto) {
    const t = (texto || "").trim();
    const ano = (t.match(/\d{4}/) || [""])[0];
    const letras = t.match(/[A-Za-zÀ-ÿ]{3,}/);
    const numero = t.match(/\b\d{1,2}\b/);
    const mes = letras ? normalizaMes(letras[0]) : (numero ? normalizaMes(numero[0]) : "");
    return { mes, ano };
  }

  /** Converte um periodo antigo ("Fev 2025 - Atual") nas partes de hoje. */
  function partesDoPeriodo(texto) {
    const [de, ate = ""] = String(texto).split(/\s*[-–—]\s*/);
    const inicio = parteData(de);
    const fim = parteData(ate);
    return {
      mes: inicio.mes, ano: inicio.ano,
      inicio_mes: inicio.mes, inicio_ano: inicio.ano,
      fim_mes: fim.mes, fim_ano: fim.ano,
      atual: RX_ATUAL.test(ate),
    };
  }

  /** Término bloqueado quando "Atual" está marcado; ano obrigatório se há mês. */
  function sincronizar(item) {
    const atual = item.querySelector('[data-campo="atual"]');
    if (atual) {
      item.querySelectorAll('[data-campo="fim_mes"], [data-campo="fim_ano"]').forEach((c) => {
        c.disabled = atual.checked;
        if (atual.checked) c.value = "";
      });
      item.querySelector(".periodo")?.classList.toggle("sem-fim", atual.checked);
    }
    for (const [campoMes, campoAno] of Object.entries(ANO_DO_MES)) {
      const mes = item.querySelector(`[data-campo="${campoMes}"]`);
      const ano = item.querySelector(`[data-campo="${campoAno}"]`);
      if (mes && ano) ano.required = !!mes.value;
    }
  }

  // --- itens repetíveis --------------------------------------------------------
  const ler = (campo) => (campo.type === "checkbox" ? campo.checked : campo.value);

  function escrever(campo, valor) {
    if (campo.type === "checkbox") {
      campo.checked = valor === true || valor === "true" || valor === "on" || valor === 1;
    } else {
      campo.value = valor ?? "";
    }
  }

  function adicionar(secao, valores = {}) {
    const tpl = document.getElementById(`tpl-${secao}`);
    const item = tpl.content.firstElementChild.cloneNode(true);
    const acoes = item.querySelector(".acoes");
    acoes.append(botao("sobe", "↑", "Mover para cima"), botao("desce", "↓", "Mover para baixo"), botao("rem", "Remover", "Remover item"));
    item.querySelectorAll("select[data-meses]").forEach(mesesNoSelect);

    const campos = [...item.querySelectorAll("[data-campo]")];
    const nomes = new Set(campos.map((c) => c.dataset.campo));
    const antigo = valores.periodo ?? valores.data;
    const dados = (antigo && !nomes.has("periodo") && !nomes.has("data"))
      ? { ...partesDoPeriodo(antigo), ...valores }
      : valores;
    campos.forEach((c) => escrever(c, dados[c.dataset.campo]));

    sincronizar(item);
    lista(secao).appendChild(item);
    renumerar(secao);
    return item;
  }

  function coletar() {
    const dados = { pessoal: {} };
    form.querySelectorAll('[data-grupo="pessoal"]').forEach((c) => { dados.pessoal[c.name] = c.value; });
    dados.resumo = form.elements.resumo.value;
    for (const secao of SECOES) {
      dados[secao] = [...lista(secao).children].map((item) => {
        const obj = {};
        item.querySelectorAll("[data-campo]").forEach((c) => { obj[c.dataset.campo] = ler(c); });
        return obj;
      });
    }
    return dados;
  }

  function preencher(dados) {
    form.querySelectorAll('[data-grupo="pessoal"]').forEach((c) => { c.value = dados.pessoal?.[c.name] ?? ""; });
    form.elements.resumo.value = dados.resumo ?? "";
    for (const secao of SECOES) {
      lista(secao).replaceChildren();
      (Array.isArray(dados[secao]) ? dados[secao] : []).forEach((v) => adicionar(secao, v || {}));
    }
  }

  function estadoInicial() {
    preencher({});
    INICIAIS.forEach((s) => adicionar(s));
  }

  // --- rascunho no navegador ---------------------------------------------------
  let timer;
  function salvar() {
    clearTimeout(timer);
    timer = setTimeout(() => {
      try { localStorage.setItem(CHAVE, JSON.stringify(coletar())); } catch (_) { /* modo privado etc. */ }
    }, 300);
  }

  function carregar() {
    for (const chave of [CHAVE, CHAVE_ANTIGA]) {
      try {
        const salvo = JSON.parse(localStorage.getItem(chave));
        if (salvo && typeof salvo === "object") {
          preencher(salvo);
          if (chave === CHAVE_ANTIGA) salvar(); // migra para a chave nova
          return true;
        }
      } catch (_) { /* ignora rascunho corrompido */ }
    }
    return false;
  }

  // --- eventos ----------------------------------------------------------------
  form.addEventListener("input", (e) => {
    if (status.className === "erro") setStatus("");
    const item = e.target.closest(".item");
    if (item) sincronizar(item);
    salvar();
  });

  form.addEventListener("change", (e) => {
    const item = e.target.closest(".item");
    if (item) sincronizar(item);
    salvar();
  });

  form.addEventListener("click", (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      const item = adicionar(add.dataset.add);
      item.querySelector("input, textarea, select")?.focus();
      salvar();
      return;
    }
    const item = e.target.closest(".item");
    if (!item) return;
    const secao = item.parentElement.dataset.secao;
    if (e.target.closest(".rem")) {
      item.remove();
    } else if (e.target.closest(".sobe") && item.previousElementSibling) {
      item.previousElementSibling.before(item);
    } else if (e.target.closest(".desce") && item.nextElementSibling) {
      item.nextElementSibling.after(item);
    } else {
      return;
    }
    renumerar(secao);
    salvar();
  });

  document.getElementById("limpar").addEventListener("click", () => {
    if (!confirm("Apagar tudo o que foi preenchido?")) return;
    try {
      localStorage.removeItem(CHAVE);
      localStorage.removeItem(CHAVE_ANTIGA);
    } catch (_) {}
    estadoInicial();
    setStatus("Formulário limpo.");
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.reportValidity()) {
      setStatus("Confira os campos obrigatórios (*) e os anos das datas que você começou a preencher.", "erro");
      return;
    }
    btnGerar.disabled = true;
    setStatus("Gerando PDF...");
    try {
      const resp = await fetch("gerar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(coletar()),
      });
      if (!resp.ok) {
        const corpo = await resp.json().catch(() => ({}));
        throw new Error(corpo.erro || `Erro ${resp.status} ao gerar o PDF.`);
      }
      const blob = await resp.blob();
      const disp = resp.headers.get("Content-Disposition") || "";
      const nome = (disp.match(/filename="?([^";]+)"?/) || [])[1] || "Curriculo.pdf";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = nome;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      setStatus(`Pronto! ${nome} foi baixado.`, "ok");
    } catch (err) {
      setStatus(err.message || "Falha de conexão. Tente novamente.", "erro");
    } finally {
      btnGerar.disabled = false;
    }
  });

  if (!carregar()) estadoInicial();
})();
