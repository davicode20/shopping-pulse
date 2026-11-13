// Shopping Pulse — scripts compartilhados entre visitante e painel.

function obterCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
}

// POST com formulário (o Django lê em request.POST) e resposta em JSON.
async function enviar(url, dados) {
    const corpo = new URLSearchParams(dados);
    const resposta = await fetch(url, {
        method: "POST",
        headers: { "X-CSRFToken": obterCsrfToken(), "X-Requested-With": "fetch" },
        body: corpo,
    });
    if (!resposta.ok) throw new Error("Falha na requisição: " + resposta.status);
    return resposta.json();
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
    const cores = ["#6c2bd9", "#ff3d7f", "#ffb800", "#13b47e", "#29c6ff"];
    for (let i = 0; i < quantidade; i++) {
        const c = document.createElement("div");
        c.className = "confete";
        c.style.left = Math.random() * 100 + "vw";
        c.style.background = cores[i % cores.length];
        c.style.animationDuration = 1.8 + Math.random() * 1.8 + "s";
        c.style.animationDelay = Math.random() * 0.4 + "s";
        document.body.appendChild(c);
        setTimeout(() => c.remove(), 4200);
    }
}

// Botões de coração (interesse) em qualquer página do visitante:
// <button class="btn-coracao" data-evento="ID" data-url="...">
document.addEventListener("click", async (e) => {
    const botao = e.target.closest(".btn-coracao");
    if (!botao) return;
    e.preventDefault();
    const ativo = botao.classList.contains("ativo");
    botao.classList.toggle("ativo", !ativo);
    botao.querySelector("i").className = ativo ? "bi bi-heart" : "bi bi-heart-fill";
    botao.classList.remove("pop"); void botao.offsetWidth; botao.classList.add("pop");
    try {
        const r = await enviar(botao.dataset.url, { evento_id: botao.dataset.evento, acao: ativo ? "remover" : "interesse" });
        document.querySelectorAll(`[data-total-interessados="${botao.dataset.evento}"]`)
            .forEach(el => el.textContent = formatarNumero(r.total_interessados));
        mostrarToast(ativo ? "Interesse removido" : "💜 Interesse registrado!");
    } catch (err) {
        botao.classList.toggle("ativo", ativo);
        mostrarToast("Não foi possível registrar. Tente de novo.");
    }
});

// Faixa etária opcional (chips no card "Conte um pouco sobre você")
document.addEventListener("click", async (e) => {
    const chip = e.target.closest("[data-faixa]");
    if (!chip) return;
    e.preventDefault();
    const card = chip.closest(".card-faixa");
    try {
        await enviar(card.dataset.url, { faixa_etaria: chip.dataset.faixa });
        card.style.transition = "opacity .3s, transform .3s";
        card.style.opacity = 0; card.style.transform = "scale(.96)";
        setTimeout(() => card.remove(), 300);
        if (chip.dataset.faixa !== "pular") mostrarToast("Obrigado! Isso ajuda o shopping a planejar melhor.");
    } catch (err) { mostrarToast("Não foi possível salvar agora."); }
});
