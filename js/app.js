/* ============================================================
   Nota Técnica · Obras em Teresina
   App principal
   ============================================================ */

const CONFIG = {
  arquivoDados: "data/obras_teresina.geojson",
  centroTeresina: [-5.0892, -42.8019],
  zoomInicial: 12,
  zoomObra: 16,
};

// Paleta por origem (sincronizada com style.css)
const CORES_ORIGEM = {
  "SIMO - Concluída":  "#0f3d2e",
  "SIMO - Execução":   "#b8741a",
  "Convênio":          "#1f4068",
  "TD - Concluído":    "#1d5a45",
  "TD - Execução":     "#a83a2a",
};

const CLASSE_ORIGEM = {
  "SIMO - Concluída":  "obra-card__origem--simo-concluida",
  "SIMO - Execução":   "obra-card__origem--simo-execucao",
  "Convênio":          "obra-card__origem--convenio",
  "TD - Concluído":    "obra-card__origem--td-concluido",
  "TD - Execução":     "obra-card__origem--td-execucao",
};

// Estado global
let obras = [];          // lista completa
let obrasFiltradas = []; // lista após filtros
let marcadores = new Map(); // id -> marker
let clusterGroup = null;
let mapa = null;
let obraAtivaId = null;

// ============================================================
// Utilitários
// ============================================================
const fmtBRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function formatarValor(v) {
  if (v == null || isNaN(v)) return "—";
  return fmtBRL.format(v);
}

function formatarData(s) {
  if (!s) return "—";
  try {
    const [a, m, d] = s.split("-");
    return `${d}/${m}/${a}`;
  } catch { return s; }
}

function tornarUnico(arr) {
  return [...new Set(arr.filter(x => x && x !== "nan"))].sort((a, b) => a.localeCompare(b, "pt-BR"));
}

function gerarId(obra, idx) {
  return `${obra.properties.origem}-${obra.properties.id_externo || idx}-${idx}`;
}

function normalizarBusca(s) {
  return (s || "").toString().toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// ============================================================
// Inicialização do mapa
// ============================================================
function iniciarMapa() {
  mapa = L.map("mapa", {
    center: CONFIG.centroTeresina,
    zoom: CONFIG.zoomInicial,
    zoomControl: true,
    preferCanvas: false,
  });

  // Tile sóbrio (Carto Voyager combina com a estética editorial)
  L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
    maxZoom: 20,
    subdomains: "abcd",
  }).addTo(mapa);

  clusterGroup = L.markerClusterGroup({
    maxClusterRadius: 50,
    iconCreateFunction: function (cluster) {
      const count = cluster.getChildCount();
      const tamanho = count < 10 ? 32 : count < 50 ? 40 : 48;
      return L.divIcon({
        html: `<div>${count}</div>`,
        className: "marker-cluster-custom",
        iconSize: L.point(tamanho, tamanho),
      });
    },
  });
  mapa.addLayer(clusterGroup);
}

// ============================================================
// Carregamento dos dados
// ============================================================
async function carregarDados() {
  const resp = await fetch(CONFIG.arquivoDados);
  const geo = await resp.json();
  obras = geo.features.map((f, idx) => ({
    ...f,
    _id: gerarId(f, idx),
    _idx: idx,
  }));
}

// ============================================================
// Construção dos marcadores
// ============================================================
function criarMarcador(obra) {
  const cor = CORES_ORIGEM[obra.properties.origem] || "#1a1814";
  const icon = L.divIcon({
    className: "",
    html: `<div class="marcador-obra" style="background:${cor};"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
  const [lon, lat] = obra.geometry.coordinates;
  const marker = L.marker([lat, lon], { icon, riseOnHover: true });
  marker.bindPopup(() => construirPopup(obra), { maxWidth: 340 });
  marker.on("click", () => destacarObra(obra._id, { centralizar: false }));
  marker.on("popupclose", () => {
    if (obraAtivaId === obra._id) {
      obraAtivaId = null;
      atualizarMarcadoresAtivos();
      atualizarCardsAtivos();
    }
  });
  return marker;
}

function construirPopup(obra) {
  const p = obra.properties;
  const exec = p.execucao_pct;
  const barra = exec != null
    ? `<div class="popup__barra"><div class="popup__barra-preenchida" style="width:${Math.min(100, exec)}%"></div></div>`
    : "";

  const linhas = [];
  if (p.orgao) linhas.push(["Órgão", p.orgao]);
  if (p.bairro) linhas.push(["Bairro", p.bairro]);
  if (p.zona) linhas.push(["Zona", p.zona]);
  if (p.status) linhas.push(["Situação", p.status]);
  if (p.valor_contrato != null) linhas.push(["Contrato", `<span class="popup__valor">${formatarValor(p.valor_contrato)}</span>`]);
  if (p.valor_pago != null) linhas.push(["Pago", `<span class="popup__valor">${formatarValor(p.valor_pago)}</span>`]);
  if (exec != null) linhas.push(["Execução", `<span class="popup__valor">${exec.toFixed(1)}%</span>${barra}`]);
  if (p.data) linhas.push(["Data", formatarData(p.data)]);
  if (p.id_externo) linhas.push(["ID", `<span class="popup__valor">${p.id_externo}</span>`]);

  const grade = linhas.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
  const link = p.link
    ? `<a class="popup__link" href="${p.link}" target="_blank" rel="noopener">Ver no Transferegov ↗</a>`
    : "";

  return `
    <div class="popup__rotulo">${p.origem}</div>
    <h3 class="popup__titulo">${(p.descricao || "Sem descrição").substring(0, 180)}${p.descricao && p.descricao.length > 180 ? "…" : ""}</h3>
    <dl class="popup__grade">${grade}</dl>
    ${link}
  `;
}

// ============================================================
// Lista lateral
// ============================================================
function renderizarLista() {
  const container = document.getElementById("lista-container");
  const contagem = document.getElementById("lista-contagem");
  contagem.textContent = `${obrasFiltradas.length} de ${obras.length}`;

  if (obrasFiltradas.length === 0) {
    container.innerHTML = `<p class="lista__vazio">Nenhuma obra encontrada com os filtros atuais.</p>`;
    return;
  }

  // Renderiza no máximo 300 cards por vez para performance
  const limite = 300;
  const aMostrar = obrasFiltradas.slice(0, limite);
  const aviso = obrasFiltradas.length > limite
    ? `<p class="lista__vazio">Exibindo as primeiras ${limite}. Refine os filtros para ver mais.</p>`
    : "";

  const html = aMostrar.map(obra => {
    const p = obra.properties;
    const classeOrigem = CLASSE_ORIGEM[p.origem] || "";
    const local = [p.bairro, p.zona].filter(x => x && x !== "nan").join(" · ") || "Localização aproximada";
    const valor = p.valor_contrato ?? p.valor_pago;
    const valorHtml = valor != null ? `<span class="obra-card__valor">${formatarValor(valor)}</span>` : "";
    const desc = (p.descricao || "Sem descrição").substring(0, 200);
    const ativo = obra._id === obraAtivaId ? "ativo" : "";

    return `
      <article class="obra-card ${ativo}" data-id="${obra._id}">
        <div class="obra-card__cabecalho">
          <span class="obra-card__origem ${classeOrigem}">${p.origem}</span>
          ${p.orgao ? `<span class="obra-card__orgao">${p.orgao}</span>` : ""}
        </div>
        <p class="obra-card__descricao">${desc}</p>
        <div class="obra-card__rodape">
          <span class="obra-card__local">${local}</span>
          ${valorHtml}
        </div>
      </article>
    `;
  }).join("");

  container.innerHTML = html + aviso;

  // Bind clicks
  container.querySelectorAll(".obra-card").forEach(card => {
    card.addEventListener("click", () => {
      const id = card.getAttribute("data-id");
      destacarObra(id, { centralizar: true });
    });
  });
}

function atualizarCardsAtivos() {
  document.querySelectorAll(".obra-card").forEach(card => {
    card.classList.toggle("ativo", card.getAttribute("data-id") === obraAtivaId);
  });
}

// ============================================================
// Destaque (clique no card ou marcador)
// ============================================================
function destacarObra(id, { centralizar }) {
  obraAtivaId = id;
  const obra = obras.find(o => o._id === id);
  if (!obra) return;

  atualizarCardsAtivos();
  atualizarMarcadoresAtivos();

  const marker = marcadores.get(id);
  if (!marker) return;

  if (centralizar) {
    const [lon, lat] = obra.geometry.coordinates;
    mapa.flyTo([lat, lon], CONFIG.zoomObra, { duration: 0.8 });
    // espera o cluster expandir, então abre popup
    setTimeout(() => {
      clusterGroup.zoomToShowLayer(marker, () => marker.openPopup());
    }, 400);
  } else {
    marker.openPopup();
  }
}

function atualizarMarcadoresAtivos() {
  marcadores.forEach((marker, id) => {
    const el = marker.getElement();
    if (!el) return;
    const div = el.querySelector(".marcador-obra");
    if (!div) return;
    div.classList.toggle("marcador-obra--ativo", id === obraAtivaId);
  });
}

// ============================================================
// Filtros
// ============================================================
function preencherSelect(idSelect, valores) {
  const sel = document.getElementById(idSelect);
  const atual = sel.value;
  // mantém a opção "Todas"/"Todos"
  const opcaoVazia = sel.querySelector('option[value=""]').outerHTML;
  sel.innerHTML = opcaoVazia + valores
    .map(v => `<option value="${v.replace(/"/g, "&quot;")}">${v}</option>`)
    .join("");
  if (valores.includes(atual)) sel.value = atual;
}

function popularFiltros() {
  const origens = tornarUnico(obras.map(o => o.properties.origem));
  const categorias = tornarUnico(obras.map(o => o.properties.categoria));
  const orgaos = tornarUnico(obras.map(o => o.properties.orgao));
  const status = tornarUnico(obras.map(o => o.properties.status));
  const zonas = tornarUnico(obras.map(o => o.properties.zona).map(z => z ? z.split(/[,;]/)[0].trim() : ""));

  preencherSelect("filtro-origem", origens);
  preencherSelect("filtro-categoria", categorias);
  preencherSelect("filtro-orgao", orgaos);
  preencherSelect("filtro-status", status);
  preencherSelect("filtro-zona", zonas);
}

function aplicarFiltros() {
  const busca = normalizarBusca(document.getElementById("busca").value);
  const fOrigem = document.getElementById("filtro-origem").value;
  const fCategoria = document.getElementById("filtro-categoria").value;
  const fOrgao = document.getElementById("filtro-orgao").value;
  const fStatus = document.getElementById("filtro-status").value;
  const fZona = document.getElementById("filtro-zona").value;

  obrasFiltradas = obras.filter(o => {
    const p = o.properties;
    if (fOrigem && p.origem !== fOrigem) return false;
    if (fCategoria && p.categoria !== fCategoria) return false;
    if (fOrgao && p.orgao !== fOrgao) return false;
    if (fStatus && p.status !== fStatus) return false;
    if (fZona && !(p.zona || "").toUpperCase().includes(fZona.toUpperCase())) return false;
    if (busca) {
      const corpus = normalizarBusca([
        p.descricao, p.orgao, p.bairro, p.zona, p.categoria, p.status, p.id_externo
      ].join(" "));
      if (!corpus.includes(busca)) return false;
    }
    return true;
  });

  renderizarMarcadores();
  renderizarLista();
  atualizarIndicadores();
}

// ============================================================
// Marcadores (resincronia após filtros)
// ============================================================
function renderizarMarcadores() {
  clusterGroup.clearLayers();
  marcadores.clear();
  const novos = [];
  obrasFiltradas.forEach(o => {
    const m = criarMarcador(o);
    marcadores.set(o._id, m);
    novos.push(m);
  });
  clusterGroup.addLayers(novos);
}

// ============================================================
// Indicadores do cabeçalho
// ============================================================
function atualizarIndicadores() {
  const total = obrasFiltradas.length;
  const valorTotal = obrasFiltradas.reduce((acc, o) => acc + (o.properties.valor_contrato ?? o.properties.valor_pago ?? 0), 0);
  const concluidas = obrasFiltradas.filter(o => /conclu/i.test(o.properties.origem) || /conclu/i.test(o.properties.status)).length;
  const emExec = total - concluidas;

  const el = document.getElementById("indicadores-cabecalho");
  el.innerHTML = `
    <div class="indicador">
      <div class="indicador__valor">${total.toLocaleString("pt-BR")}</div>
      <div class="indicador__rotulo">Obras listadas</div>
    </div>
    <div class="indicador">
      <div class="indicador__valor">${concluidas.toLocaleString("pt-BR")}</div>
      <div class="indicador__rotulo">Concluídas</div>
    </div>
    <div class="indicador">
      <div class="indicador__valor">${emExec.toLocaleString("pt-BR")}</div>
      <div class="indicador__rotulo">Em andamento</div>
    </div>
    <div class="indicador">
      <div class="indicador__valor">${fmtBRL.format(valorTotal).replace("R$", "R$ ")}</div>
      <div class="indicador__rotulo">Valor consolidado</div>
    </div>
  `;
}

// ============================================================
// Legenda do mapa
// ============================================================
function renderizarLegenda() {
  const ul = document.querySelector("#mapa-legenda ul");
  ul.innerHTML = Object.entries(CORES_ORIGEM)
    .map(([nome, cor]) => `<li style="--cor-pin:${cor}">${nome}</li>`)
    .join("");
}

// ============================================================
// Bindings
// ============================================================
function vincularEventos() {
  const busca = document.getElementById("busca");
  let timer;
  busca.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(aplicarFiltros, 180);
  });

  ["filtro-origem", "filtro-categoria", "filtro-orgao", "filtro-status", "filtro-zona"]
    .forEach(id => document.getElementById(id).addEventListener("change", aplicarFiltros));

  document.getElementById("limpar-filtros").addEventListener("click", () => {
    document.getElementById("busca").value = "";
    ["filtro-origem", "filtro-categoria", "filtro-orgao", "filtro-status", "filtro-zona"]
      .forEach(id => document.getElementById(id).value = "");
    aplicarFiltros();
  });
}

// ============================================================
// Boot
// ============================================================
(async function main() {
  iniciarMapa();
  renderizarLegenda();
  try {
    await carregarDados();
    obrasFiltradas = obras.slice();
    popularFiltros();
    vincularEventos();
    renderizarMarcadores();
    renderizarLista();
    atualizarIndicadores();
  } catch (err) {
    console.error(err);
    document.getElementById("lista-container").innerHTML =
      `<p class="lista__vazio">Erro ao carregar dados. Verifique se o arquivo <code>data/obras_teresina.geojson</code> existe.</p>`;
  }
})();
