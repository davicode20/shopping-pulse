// ShoppDash — scripts compartilhados entre visitante e painel.

function obterCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
}

// POST com formulário (o Django lê em request.POST) e resposta em JSON.
// Tem tempo limite: no Wi-Fi do evento, um botão não pode ficar "travado" esperando para sempre.
async function enviar(url, dados, tempoLimite = 10000) {
    const controle = new AbortController();
    const timer = setTimeout(() => controle.abort(), tempoLimite);
    try {
        const resposta = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": obterCsrfToken(), "X-Requested-With": "fetch" },
            body: new URLSearchParams(dados),
            credentials: "same-origin",
            signal: controle.signal,
        });
        if (!resposta.ok) throw new Error("Falha na requisição: " + resposta.status);
        return await resposta.json();
    } finally {
        clearTimeout(timer);
    }
}

// Executa a ação de um botão uma vez por vez (evita toque duplo / requisições cruzadas).
async function comBotao(botao, acao) {
    if (botao.dataset.ocupado) return;
    botao.dataset.ocupado = "1";
    botao.classList.add("ocupado");
    botao.setAttribute("aria-busy", "true");
    try {
        return await acao();
    } catch (err) {
        mostrarToast("Não foi possível registrar. Verifique a conexão e tente de novo.");
    } finally {
        delete botao.dataset.ocupado;
        botao.classList.remove("ocupado");
        botao.removeAttribute("aria-busy");
    }
}

function atualizarTotal(eventoId, total) {
    document.querySelectorAll(`[data-total-interessados="${eventoId}"]`)
        .forEach(el => el.textContent = formatarNumero(total));
}

function mostrarToast(texto) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = texto;
    toast.classList.add("visivel");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove("visivel"), 2200);
}

function formatarNumero(valor, casas = 0) {
    if (valor === null || valor === undefined) return "—";
    return Number(valor).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

function confete(quantidade = 70) {
    const cores = ["#e8870f", "#ffc46b", "#c4620c", "#fbefe2", "#b4530a", "#ffffff"];
    for (let i = 0; i < quantidade; i++) {
        const c = document.createElement("div");
        c.className = "confete";
        c.style.left = Math.random() * (window.innerWidth - 12) + "px"; // sem passar da borda (rolagem lateral)
        c.style.background = cores[i % cores.length];
        c.style.animationDuration = 1.8 + Math.random() * 1.8 + "s";
        c.style.animationDelay = Math.random() * 0.4 + "s";
        document.body.appendChild(c);
        setTimeout(() => c.remove(), 4200);
    }
}

// Botões de coração (interesse) em qualquer página do visitante:
// <button class="btn-coracao" data-evento="ID" data-url="...">
function pintarCoracao(botao, ativo) {
    botao.classList.toggle("ativo", ativo);
    botao.querySelector("i").className = ativo ? "bi bi-heart-fill" : "bi bi-heart";
    botao.setAttribute("aria-pressed", ativo ? "true" : "false");
}

document.addEventListener("click", (e) => {
    const botao = e.target.closest(".btn-coracao");
    if (!botao) return;
    e.preventDefault();
    if (botao.dataset.ocupado) return;
    const ativo = botao.classList.contains("ativo");
    pintarCoracao(botao, !ativo); // resposta imediata; desfaz se o servidor falhar
    botao.classList.remove("pop"); void botao.offsetWidth; botao.classList.add("pop");
    comBotao(botao, async () => {
        try {
            const r = await enviar(botao.dataset.url, { evento_id: botao.dataset.evento, acao: ativo ? "remover" : "interesse" });
            pintarCoracao(botao, r.interessado);
            atualizarTotal(botao.dataset.evento, r.total_interessados);
            mostrarToast(r.interessado ? "💜 Interesse registrado!" : "Interesse removido");
        } catch (err) {
            pintarCoracao(botao, ativo);
            throw err;
        }
    });
});

// Faixa etária opcional (chips no card "Conte um pouco sobre você")
document.addEventListener("click", async (e) => {
    const chip = e.target.closest("[data-faixa]");
    if (!chip) return;
    e.preventDefault();
    const card = chip.closest(".card-faixa");
    if (!card || card.dataset.ocupado) return;
    card.dataset.ocupado = "1";
    try {
        await enviar(card.dataset.url, { faixa_etaria: chip.dataset.faixa });
        card.style.transition = "opacity .3s, transform .3s";
        card.style.opacity = 0; card.style.transform = "scale(.96)";
        setTimeout(() => card.remove(), 300);
        if (chip.dataset.faixa !== "pular") mostrarToast("Obrigado! Isso ajuda o shopping a planejar melhor.");
    } catch (err) {
        delete card.dataset.ocupado;
        mostrarToast("Não foi possível salvar agora.");
    }
});

// Botão "voltar": volta no histórico só se viemos de uma página do próprio site
// (quem chega pelo QR Code ou por um link compartilhado vai para o início).
document.addEventListener("click", (e) => {
    const link = e.target.closest("[data-voltar]");
    if (!link) return;
    let mesmoSite = false;
    try { mesmoSite = document.referrer && new URL(document.referrer).origin === location.origin; } catch (err) { /* ignora */ }
    if (mesmoSite && history.length > 1) {
        e.preventDefault();
        history.back();
    }
});

// Carrosséis horizontais (.carrossel): bolinhas de posição, setas no desktop e arrastar com o mouse.
// No celular o deslizar com o dedo continua nativo; o JS só acrescenta o que faltava.
function iniciarCarrossel(el) {
    const cards = Array.from(el.children);
    if (cards.length < 2) return;

    const area = document.createElement("div");
    area.className = "carrossel-area";
    el.parentNode.insertBefore(area, el);
    area.appendChild(el);
    // Links e imagens dentro do carrossel não podem iniciar o "arrastar" nativo do navegador,
    // que cancela os eventos do mouse e impede o arrasto do carrossel
    el.querySelectorAll("a, img").forEach(n => { n.draggable = false; });
    el.addEventListener("dragstart", e => e.preventDefault());

    const passo = () => cards[1].offsetLeft - cards[0].offsetLeft;
    // Rolagem instantânea: o snap do CSS encaixa o card certo em qualquer navegador
    const irPara = i => el.scrollTo({ left: cards[i].offsetLeft - cards[0].offsetLeft });

    const pontos = document.createElement("div");
    pontos.className = "carrossel-pontos";
    const bolinhas = cards.map((_, i) => {
        const b = document.createElement("button");
        b.type = "button";
        b.setAttribute("aria-label", `Ir para o item ${i + 1}`);
        b.addEventListener("click", () => irPara(i));
        pontos.appendChild(b);
        return b;
    });
    area.appendChild(pontos);

    const criarSeta = (classe, rotulo, icone) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = `carrossel-seta ${classe}`;
        b.setAttribute("aria-label", rotulo);
        b.innerHTML = `<i class="bi ${icone}"></i>`;
        area.appendChild(b);
        return b;
    };
    const anterior = criarSeta("anterior", "Anterior", "bi-chevron-left");
    const proximo = criarSeta("proximo", "Próximo", "bi-chevron-right");
    anterior.addEventListener("click", () => el.scrollBy({ left: -passo() }));
    proximo.addEventListener("click", () => el.scrollBy({ left: passo() }));

    const atualizar = () => {
        const max = el.scrollWidth - el.clientWidth;
        const i = Math.min(cards.length - 1, Math.max(0, Math.round(el.scrollLeft / passo())));
        bolinhas.forEach((b, k) => b.classList.toggle("ativo", k === i));
        anterior.disabled = el.scrollLeft <= 4;
        proximo.disabled = el.scrollLeft >= max - 4;
    };
    el.addEventListener("scroll", atualizar, { passive: true });
    window.addEventListener("resize", atualizar);
    atualizar();

    // Arrastar com o mouse (toque continua nativo)
    let x0 = 0, sl0 = 0, arrastando = false, moveu = false;
    el.addEventListener("pointerdown", e => {
        if (e.pointerType !== "mouse" || e.button !== 0) return;
        arrastando = true; moveu = false; x0 = e.clientX; sl0 = el.scrollLeft;
        el.classList.add("arrastando");
    });
    el.addEventListener("pointermove", e => {
        if (!arrastando) return;
        const dx = e.clientX - x0;
        if (Math.abs(dx) > 5) moveu = true;
        el.scrollLeft = sl0 - dx;
    });
    const soltar = () => {
        if (!arrastando) return;
        arrastando = false;
        el.classList.remove("arrastando");
    };
    el.addEventListener("pointerup", soltar);
    el.addEventListener("pointerleave", soltar);
    el.addEventListener("pointercancel", soltar);
    // Depois de arrastar, o clique que sobra não deve abrir o card
    el.addEventListener("click", e => {
        if (moveu) { e.preventDefault(); e.stopPropagation(); moveu = false; }
    }, true);
}

document.querySelectorAll(".carrossel").forEach(iniciarCarrossel);

// Menu lateral do painel: destaca a seção que está na tela (Painel, Recomendações da IA ou Validação de demanda)
function iniciarMenuAdmin() {
    const links = Array.from(document.querySelectorAll(".sidebar nav a[data-spy]"));
    const ia = document.getElementById("ia");
    const demanda = document.getElementById("demanda");
    if (!links.length || !ia || !demanda) return; // só existe na tela do painel
    const marcar = () => {
        const limite = 140; // altura em que a seção já está "em foco" no topo da tela
        let ativo = "topo";
        if (demanda.getBoundingClientRect().top <= limite) ativo = "demanda";
        else if (ia.getBoundingClientRect().top <= limite) ativo = "ia";
        links.forEach(a => a.classList.toggle("ativo", a.dataset.spy === ativo));
    };
    window.addEventListener("scroll", marcar, { passive: true });
    marcar();
}
iniciarMenuAdmin();
