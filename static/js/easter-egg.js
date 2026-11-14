// Easter Egg "A Maldição do ShoppDash" (Sexta-feira 13).
// Carregado só na Home: 13 cliques seguidos no logotipo do cabeçalho, dentro de 5 segundos.
// Tudo fica num overlay criado e removido por este script; a Home não é alterada.
(function () {
    const CLIQUES_PARA_ATIVAR = 13;
    const JANELA_MS = 5000;

    const logo = document.querySelector(".topbar .logo");
    if (!logo) return;

    let cliques = 0;
    let inicioJanela = 0;
    let overlay = null;
    let timers = [];
    let focoAnterior = null;
    let overflowAnterior = "";

    const reduzirMovimento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const agendar = (fn, ms) => timers.push(setTimeout(fn, ms));
    const limparTimers = () => { timers.forEach(clearTimeout); timers = []; };

    logo.addEventListener("click", (e) => {
        // Cliques com modificadores (nova aba, clique do meio etc.) seguem o comportamento normal
        if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
        // O logotipo aponta para a própria Home: sem recarregar a página, a contagem se mantém
        e.preventDefault();
        if (overlay) return;

        const agora = Date.now();
        if (cliques === 0 || agora - inicioJanela > JANELA_MS) {
            cliques = 0;               // a janela de 5 s estourou: recomeça a contagem
            inicioJanela = agora;
        }
        cliques++;
        if (cliques === CLIQUES_PARA_ATIVAR) {
            cliques = 0;
            abrir();
        }
    });

    function abrir() {
        const reduzir = reduzirMovimento();
        focoAnterior = document.activeElement;
        overflowAnterior = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        overlay = document.createElement("div");
        overlay.className = "ee-overlay ee-tenso";   // "tenso": suspense com pulsação lenta
        overlay.tabIndex = -1;
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.setAttribute("aria-labelledby", "ee-titulo");
        overlay.innerHTML = `
            <button type="button" class="ee-fechar" aria-label="Fechar a experiência">
                <i class="bi bi-x-lg" aria-hidden="true"></i>
            </button>
            <div class="ee-palco">
                <div class="ee-cavalo"><span class="ee-olho"></span></div>
                <p class="ee-nome">Shopp<span>Death</span></p>
            </div>
            <div class="ee-mensagem">
                <h2 id="ee-titulo">💀 VOCÊ DESPERTOU A MALDIÇÃO DA SEXTA-FEIRA 13!</h2>
                <p>Nem todas as experiências do shopping deveriam ser descobertas...</p>
                <button type="button" class="ee-quebrar">QUEBRAR A MALDIÇÃO</button>
            </div>`;

        // Reaproveita o cavalo vetorial já usado no logotipo (sem duplicar o desenho)
        const cavalo = logo.querySelector(".cavalo-vetor");
        if (cavalo) overlay.querySelector(".ee-cavalo").prepend(cavalo.cloneNode(true));

        overlay.querySelector(".ee-fechar").addEventListener("click", encerrar);
        overlay.querySelector(".ee-quebrar").addEventListener("click", encerrar);
        document.addEventListener("keydown", tecla);
        document.body.appendChild(overlay);
        overlay.focus();

        // Etapa 1 (suspense) -> Etapa 2 (cavalo revelado) -> Etapa 3 (mensagem e botão)
        agendar(() => {
            overlay.classList.remove("ee-tenso");
            overlay.classList.add("ee-revelar");
        }, reduzir ? 0 : 1400);
        agendar(() => overlay.classList.add("ee-mensagem-visivel"), reduzir ? 0 : 2600);
    }

    function tecla(e) {
        if (!overlay) return;
        if (e.key === "Escape") {
            e.preventDefault();
            encerrar();
            return;
        }
        if (e.key === "Tab") {
            // Mantém o foco dentro da experiência enquanto ela está aberta
            const fechar = overlay.querySelector(".ee-fechar");
            const quebrar = overlay.querySelector(".ee-quebrar");
            const ultimo = overlay.classList.contains("ee-mensagem-visivel") ? quebrar : fechar;
            if (e.shiftKey && document.activeElement === fechar) {
                e.preventDefault();
                ultimo.focus();
            } else if (!e.shiftKey && document.activeElement === ultimo) {
                e.preventDefault();
                fechar.focus();
            }
        }
    }

    // Etapa 4: desaparecimento curto e remoção de todos os efeitos
    function encerrar() {
        if (!overlay || overlay.classList.contains("ee-saindo")) return;
        limparTimers();
        overlay.classList.add("ee-saindo");
        agendar(finalizar, reduzirMovimento() ? 0 : 450);
    }

    function finalizar() {
        limparTimers();
        document.removeEventListener("keydown", tecla);
        overlay.remove();
        overlay = null;
        document.body.style.overflow = overflowAnterior;
        cliques = 0;
        if (focoAnterior && document.contains(focoAnterior)) focoAnterior.focus({ preventScroll: true });
        focoAnterior = null;
    }
})();
