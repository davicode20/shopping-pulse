// Cartões estilo "swipe": direita = interesse, esquerda = sem interesse.
// Cada decisão é enviada ao backend e alimenta o painel administrativo na hora.
(function () {
    const deck = document.getElementById("deck");
    if (!deck) return;
    const LIMITE = 110; // px para considerar a decisão

    const cartoes = () => [...deck.querySelectorAll(".swipe-card:not(.voando)")];
    const topo = () => cartoes().at(-1);

    function arrumarPilha(aposDecisao = false) {
        const lista = cartoes().reverse(); // [0] é o do topo
        lista.forEach((c, i) => {
            c.style.zIndex = 10 - i;
            if (i > 0) c.style.transform = `translateY(${Math.min(i, 2) * 10}px) scale(${1 - Math.min(i, 2) * 0.04})`;
            else c.style.transform = "";
            c.style.pointerEvents = i === 0 ? "auto" : "none";
        });
        const restantes = document.getElementById("restantes"); // o contador é opcional na tela
        if (restantes) restantes.textContent = lista.length;
        if (!lista.length) {
            document.getElementById("deckVazio").hidden = false;
            document.getElementById("deckAcoes").hidden = true;
            document.querySelector(".dica-swipe").hidden = true;
            if (aposDecisao) confete(50);
        }
    }

    function decidir(cartao, interesse) {
        if (!cartao) return;
        const direcao = interesse ? 1 : -1;
        cartao.classList.add("voando");
        cartao.style.transform = `translate(${direcao * window.innerWidth}px, -40px) rotate(${direcao * 30}deg)`;
        cartao.style.opacity = 0;
        enviar(deck.dataset.url, { evento_id: cartao.dataset.evento, acao: interesse ? "interesse" : "sem_interesse" })
            .catch(() => mostrarToast("Sem conexão: sua escolha não foi salva."));
        if (interesse) mostrarToast("💚 Anotado! " + cartao.dataset.nome);
        setTimeout(() => cartao.remove(), 400);
        arrumarPilha(true);
    }

    // Arrastar (mouse e toque) com Pointer Events
    let inicioX = 0, inicioY = 0, dx = 0, dy = 0, arrastando = null, ponteiro = null;

    deck.addEventListener("pointerdown", (e) => {
        // só o primeiro dedo / botão principal do mouse
        if (arrastando || !e.isPrimary || (e.pointerType === "mouse" && e.button !== 0)) return;
        const cartao = e.target.closest(".swipe-card");
        if (!cartao || cartao !== topo()) return;
        arrastando = cartao;
        ponteiro = e.pointerId;
        inicioX = e.clientX; inicioY = e.clientY; dx = 0; dy = 0;
        cartao.classList.remove("voltando");
        cartao.classList.add("arrastando"); // sem transição enquanto o dedo arrasta: o cartão segue o toque
        try { cartao.setPointerCapture(e.pointerId); } catch (err) { /* ponteiro já liberado */ }
    });

    deck.addEventListener("pointermove", (e) => {
        if (!arrastando || e.pointerId !== ponteiro) return;
        dx = e.clientX - inicioX; dy = e.clientY - inicioY;
        arrastando.style.transform = `translate(${dx}px, ${dy * 0.3}px) rotate(${dx / 14}deg)`;
        const forca = Math.min(Math.abs(dx) / LIMITE, 1);
        arrastando.querySelector(".selo-quero").style.opacity = dx > 0 ? forca : 0;
        arrastando.querySelector(".selo-passo").style.opacity = dx < 0 ? forca : 0;
    });

    function soltar(e) {
        if (!arrastando || e.pointerId !== ponteiro) return;
        const cartao = arrastando;
        cartao.classList.remove("arrastando");
        arrastando = null;
        ponteiro = null;
        // pointercancel (notificação, gesto do sistema, rolagem) nunca decide: o cartão só volta.
        // Antes, o clientX do cancelamento podia vir 0 e registrar um "passo" sem querer.
        const cancelado = e.type !== "pointerup";
        if (!cancelado && Math.abs(dx) > LIMITE) {
            decidir(cartao, dx > 0);
        } else {
            cartao.classList.add("voltando");
            arrumarPilha();
            cartao.querySelectorAll(".selo").forEach(s => s.style.opacity = 0);
            // toque sem arrastar: abre os detalhes
            if (!cancelado && Math.abs(dx) < 8 && Math.abs(dy) < 8) abrirDetalhe(cartao);
        }
    }
    deck.addEventListener("pointerup", soltar);
    deck.addEventListener("pointercancel", soltar);

    function abrirDetalhe(cartao) {
        if (cartao) window.location = window.URL_DETALHE.replace("/0/", `/${cartao.dataset.evento}/`);
    }

    document.getElementById("btnQuero").addEventListener("click", () => {
        const c = topo(); if (c) { c.querySelector(".selo-quero").style.opacity = 1; decidir(c, true); }
    });
    document.getElementById("btnPasso").addEventListener("click", () => {
        const c = topo(); if (c) { c.querySelector(".selo-passo").style.opacity = 1; decidir(c, false); }
    });
    document.getElementById("btnInfo").addEventListener("click", () => abrirDetalhe(topo()));

    // Teclado (útil na apresentação pelo notebook): ← e →
    document.addEventListener("keydown", (e) => {
        if (e.repeat || e.target.closest("input, textarea, select, [contenteditable]")) return;
        if (e.key === "ArrowRight") { e.preventDefault(); document.getElementById("btnQuero").click(); }
        if (e.key === "ArrowLeft") { e.preventDefault(); document.getElementById("btnPasso").click(); }
    });

    arrumarPilha();
})();
