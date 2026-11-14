// Painel administrativo: renderiza os indicadores e atualiza ao vivo a cada poucos segundos.
(function () {
    const cfg = window.PAINEL;
    const INTERVALO = 5000;
    const STATUS = { proposta: "Em validação", confirmado: "Confirmado", realizado: "Realizado" };
    const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    const brl = (v) => v ? "R$ " + formatarNumero(v, 2) : "—";
    const urlEvento = (id) => cfg.urlEvento.replace("/0/", `/${id}/`);

    let graficos = {};
    let ultimos = {};

    // Paleta Capim Dourado para os gráficos
    const COR = { ouro: "#e8870f", ouroClaro: "#ffc46b", cafe: "#4a2a14", areia: "#e6b98a", grade: "#f3ede3" };
    // Mesmos tons das capas das categorias (CSS), para o gráfico "conversar" com o resto do sistema
    const CORES_CATEGORIA = {
        "Gastronomia": "#c9774c", "Música": "#87607f", "Tecnologia": "#56758f", "Cultura": "#b4737a",
        "Esportes": "#749668", "Entretenimento": "#e8870f", "Infantil": "#66a39f",
    };
    const coresCategorias = (d) => d.categorias.labels.map((nome, i) => CORES_CATEGORIA[nome] || d.categorias.cores[i]);
    const MENOS_MOVIMENTO = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Número que "conta" até o novo valor (em vez de trocar de repente)
    function animarNumero(el, de, para, casas, sufixo) {
        if (MENOS_MOVIMENTO || de === para || typeof para !== "number") {
            el.textContent = formatarNumero(para, casas) + sufixo;
            return;
        }
        const inicio = performance.now(), duracao = 900;
        cancelAnimationFrame(el._quadro);
        const passo = (agora) => {
            const t = Math.min((agora - inicio) / duracao, 1);
            const suave = 1 - Math.pow(1 - t, 3);
            el.textContent = formatarNumero(de + (para - de) * suave, casas) + sufixo;
            if (t < 1) el._quadro = requestAnimationFrame(passo);
        };
        el._quadro = requestAnimationFrame(passo);
    }

    // ---------- Gráficos ----------
    function criarGraficos(d) {
        const ctxSerie = document.getElementById("gSerie").getContext("2d");
        const grad = ctxSerie.createLinearGradient(0, 0, 0, 260);
        grad.addColorStop(0, "rgba(232, 135, 15, .30)");
        grad.addColorStop(1, "rgba(232, 135, 15, 0)");

        graficos.serie = new Chart(ctxSerie, {
            type: "line",
            data: {
                labels: d.serie.labels,
                datasets: [
                    { label: "Interesses", data: d.serie.interesses, borderColor: COR.ouro, backgroundColor: grad, fill: true, tension: .4, borderWidth: 2.5, pointRadius: 0, pointHoverRadius: 5, pointHoverBackgroundColor: COR.ouro },
                    { label: "Check-ins", data: d.serie.checkins, borderColor: COR.cafe, backgroundColor: COR.cafe, tension: .4, borderWidth: 2.2, pointRadius: 0, pointHoverRadius: 5 },
                    { label: "Avaliações", data: d.serie.avaliacoes, borderColor: COR.areia, backgroundColor: COR.areia, tension: .4, borderWidth: 2, borderDash: [5, 4], pointRadius: 0, pointHoverRadius: 5 },
                ],
            },
            options: {
                maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
                plugins: { legend: { position: "top", align: "end" } },
                scales: { x: { grid: { display: false }, border: { display: false } }, y: { beginAtZero: true, grid: { color: COR.grade }, border: { display: false } } },
            },
        });

        graficos.categorias = new Chart(document.getElementById("gCategorias"), {
            type: "doughnut",
            data: { labels: d.categorias.labels, datasets: [{ data: d.categorias.valores, backgroundColor: coresCategorias(d), borderWidth: 3, borderColor: "#fff", hoverOffset: 8, borderRadius: 4 }] },
            options: {
                maintainAspectRatio: false, cutout: "68%",
                plugins: {
                    legend: { position: "bottom", labels: { padding: 12, boxWidth: 8 } },
                    tooltip: { callbacks: { label: (c) => ` ${c.label}: ${formatarNumero(c.raw)} interessados · ${formatarNumero(d.categorias.aprovacao[c.dataIndex], 1)}% aprovação` } },
                },
            },
        });

        graficos.top = new Chart(document.getElementById("gTop"), {
            type: "bar",
            data: {
                labels: d.top_eventos.labels,
                datasets: [
                    { label: "Interessados", data: d.top_eventos.interessados, backgroundColor: COR.ouro, borderRadius: 8, barPercentage: .7 },
                    { label: "Check-ins", data: d.top_eventos.checkins, backgroundColor: COR.cafe, borderRadius: 8, barPercentage: .7 },
                ],
            },
            options: {
                indexAxis: "y", maintainAspectRatio: false,
                plugins: { legend: { position: "top", align: "end" } },
                scales: { x: { grid: { color: COR.grade }, border: { display: false } }, y: { grid: { display: false }, border: { display: false }, ticks: { callback: function (v) { const l = this.getLabelForValue(v); return l.length > 26 ? l.slice(0, 25) + "…" : l; } } } },
            },
        });
    }

    function atualizarGraficos(d) {
        const s = graficos.serie.data;
        s.labels = d.serie.labels;
        s.datasets[0].data = d.serie.interesses; s.datasets[1].data = d.serie.checkins; s.datasets[2].data = d.serie.avaliacoes;
        const c = graficos.categorias.data;
        c.labels = d.categorias.labels; c.datasets[0].data = d.categorias.valores; c.datasets[0].backgroundColor = coresCategorias(d);
        const t = graficos.top.data;
        t.labels = d.top_eventos.labels; t.datasets[0].data = d.top_eventos.interessados; t.datasets[1].data = d.top_eventos.checkins;
        Object.values(graficos).forEach(g => g.update("none"));
    }

    // ---------- KPIs ----------
    function renderKpis(d) {
        document.querySelectorAll("[data-kpi]").forEach(el => {
            const chave = el.dataset.kpi;
            const valor = d.kpis[chave];
            const casas = Number(el.dataset.casas || 0);
            // na primeira vez conta a partir de zero; depois, do valor anterior
            animarNumero(el.querySelector(".kpi-valor"), ultimos[chave] ?? 0, valor, casas, el.dataset.sufixo || "");
            if (ultimos[chave] !== undefined && ultimos[chave] !== valor) {
                el.classList.remove("mudou"); void el.offsetWidth; el.classList.add("mudou");
            }
            ultimos[chave] = valor;
        });
        const st = d.eventos_por_status;
        document.getElementById("subEventos").textContent = `${st.proposta || 0} em validação · ${st.confirmado || 0} confirmados`;
        document.getElementById("subAvaliacoes").textContent = `${formatarNumero(d.kpis.total_avaliacoes)} avaliações`;
        document.getElementById("kpiReais").textContent = formatarNumero(d.kpis.interacoes_reais);
        document.getElementById("atualizadoEm").textContent = d.atualizado_em;
    }

    // ---------- Feed, validação e tabela ----------
    function renderFeed(d) {
        document.getElementById("feed").innerHTML = d.atividade.map(a => `
            <li class="${a.ao_vivo ? "ao-vivo-item" : ""}">
                <span class="feed-icone"><i class="bi ${a.icone}"></i></span>
                <div class="min-w-0"><div class="text-truncate">Visitante ${esc(a.texto)}</div>
                <small>${esc(a.quando)}${a.ao_vivo ? '<span class="tag-vivo">AO VIVO</span>' : ""}</small></div>
            </li>`).join("") || '<li class="text-2">Nenhuma atividade ainda.</li>';
    }

    function renderValidacao(d) {
        document.getElementById("validacao").innerHTML = d.validacao.map(p => `
            <div class="col-md-6 col-xl-4">
                <a class="demanda-item d-block text-decoration-none text-reset" href="${urlEvento(p.id)}">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="badge-status status-proposta"><i class="bi bi-lightbulb"></i> ${esc(p.categoria)}</span>
                        <small class="text-2">Investimento: <b>${brl(p.investimento)}</b></small>
                    </div>
                    <h3>${esc(p.nome)}</h3>
                    <div class="demanda-nums">
                        <div><b>${formatarNumero(p.visualizacoes)}</b><small>visualizaram</small></div>
                        <div><b style="color:var(--ouro-escuro)">${formatarNumero(p.interessados)}</b><small>interessados</small></div>
                        <div><b style="color:var(--verde)">${formatarNumero(p.presenca_provavel)}</b><small>provavelmente vão</small></div>
                    </div>
                    <div class="demanda-rodape">
                        <span><i class="bi bi-person"></i> ${p.faixa_principal ? `${formatarNumero(p.faixa_principal_pct, 1)}% têm ${esc(p.faixa_principal)} anos` : "faixa etária: sem dados"}</span>
                        <span><i class="bi bi-cash-coin"></i> ${brl(p.custo_por_presenca)}/presença</span>
                    </div>
                </a>
            </div>`).join("") || '<p class="text-2 px-2">Nenhuma ideia em validação. Publique uma para medir a demanda.</p>';
    }

    function renderTabela(d) {
        document.getElementById("tabela").innerHTML = d.eventos.map(e => `
            <tr class="clicavel" onclick="location.href='${urlEvento(e.id)}'">
                <td><strong>${esc(e.nome)}</strong><br><small class="text-2">${esc(e.categoria)}</small></td>
                <td><span class="badge-status status-${esc(e.status)}">${STATUS[e.status] || esc(e.status)}</span></td>
                <td class="text-end fw-600">${formatarNumero(e.interessados)}</td>
                <td><div class="d-flex align-items-center gap-2"><div class="barra-mini flex-grow-1"><span style="width:${e.aprovacao}%"></span></div><small>${formatarNumero(e.aprovacao, 0)}%</small></div></td>
                <td class="text-end">${e.checkins ? formatarNumero(e.checkins) : '<span class="text-2">—</span>'}</td>
                <td class="text-end">${e.comparecimento !== null ? formatarNumero(e.comparecimento, 1) + "%" : '<span class="text-2">—</span>'}</td>
                <td class="text-end">${e.nota_media !== null ? `<span class="nota-pill ${e.nota_media < 3.8 ? "nota-baixa" : ""}"><i class="bi bi-star-fill"></i>${formatarNumero(e.nota_media, 1)}</span>` : '<span class="text-2">—</span>'}</td>
            </tr>`).join("");
    }

    function renderTudo(d, primeiraVez) {
        renderKpis(d);
        if (primeiraVez) criarGraficos(d); else atualizarGraficos(d);
        renderFeed(d);
        renderValidacao(d);
        renderTabela(d);
    }

    // ---------- IA ----------
    // Sessão do admin expirou (ou logout em outra aba): volta para o login e retorna aqui depois
    function irParaLogin(urlLogin) {
        location.href = (urlLogin || "/painel/entrar/") + "?proximo=" + encodeURIComponent(location.pathname);
        return new Promise(() => {}); // interrompe quem chamou enquanto a página troca
    }
    // Resposta vazia ou não-JSON = o servidor caiu/reiniciou no meio (ex.: deploy no Render)
    async function lerJson(resposta) {
        try {
            return await resposta.json();
        } catch (err) {
            throw new Error("O servidor não respondeu (pode estar reiniciando). Aguarde alguns segundos e tente de novo.");
        }
    }
    async function buscarJson(url) {
        const resposta = await fetch(url, { headers: { "X-Requested-With": "fetch" } });
        const dados = await lerJson(resposta);
        if (resposta.status === 401) return irParaLogin(dados.login);
        return dados;
    }

    async function carregarIa(forcar) {
        const conteudo = document.getElementById("iaConteudo");
        const fonte = document.getElementById("iaFonte");
        const botao = document.getElementById("btnIa");
        botao.disabled = true;
        fonte.textContent = "analisando…";
        conteudo.innerHTML = '<div class="ia-carregando"><div class="texto"><div class="spinner-border spinner-border-sm"></div> Interpretando os indicadores calculados pela plataforma…</div><div class="esqueleto"><span></span><span></span><span></span><span></span></div></div>';
        try {
            const r = await buscarJson(cfg.urlIa + (forcar ? "?forcar=1" : ""));
            const a = r.analise;
            fonte.innerHTML = r.fonte === "gemini"
                ? `<i class="bi bi-google"></i> Google Gemini · ${esc(r.modelo)}`
                : '<i class="bi bi-cpu"></i> Modo demonstração (regras sobre os dados)';
            const prio = { alta: "Alta", media: "Média", baixa: "Baixa" };
            // Números que a checagem não encontrou nos dados: destacados onde aparecem
            const v = r.verificacao || { citados: 0, conferidos: 0, nao_encontrados: [] };
            const suspeitos = [...new Set(v.nao_encontrados.map(n => n.numero))];
            const marcar = (texto) => {
                let html = esc(texto);
                suspeitos.forEach(n => {
                    const alvo = new RegExp(`(?<![\\d.,])${n.replace(/[.]/g, "\\.")}(?![\\d])`, "g");
                    html = html.replace(alvo, `<mark class="num-suspeito" title="Número não encontrado nos dados calculados">${n}</mark>`);
                });
                return html;
            };
            const selo = !v.citados ? "" : suspeitos.length
                ? `<div class="ia-verificacao alerta"><i class="bi bi-exclamation-diamond-fill"></i>
                       <span><strong>${v.nao_encontrados.length} de ${v.citados} números citados não foram encontrados nos dados calculados</strong> (destacados no texto). Confira antes de decidir.</span></div>`
                : `<div class="ia-verificacao ok"><i class="bi bi-patch-check-fill"></i>
                       <span>${v.conferidos} de ${v.citados} números citados conferidos com os dados calculados pela plataforma.</span></div>`;
            conteudo.innerHTML = `<div class="ia-conteudo-entrada">
                ${selo}
                <p class="ia-resumo">${marcar(a.resumo)}</p>
                <div class="row g-4">
                    <div class="col-lg-4">
                        <div class="ia-subtitulo">O que os dados mostram</div>
                        <ul class="ia-lista mb-3">${(a.destaques || []).map(t => `<li><i class="bi bi-lightning-charge-fill"></i><span>${marcar(t)}</span></li>`).join("")}</ul>
                        ${(a.alertas || []).map(t => `<div class="ia-alerta mb-2"><i class="bi bi-exclamation-triangle-fill"></i><span>${marcar(t)}</span></div>`).join("")}
                    </div>
                    <div class="col-lg-5">
                        <div class="ia-subtitulo">Recomendações</div>
                        <div class="row g-2">${(a.recomendacoes || []).map(rc => `
                            <div class="col-md-6"><div class="rec-item">
                                <span class="prio prio-${esc(rc.prioridade)}">Prioridade ${prio[rc.prioridade] || esc(rc.prioridade)}</span>
                                <h3>${marcar(rc.titulo)}</h3><p>${marcar(rc.descricao)}</p>
                            </div></div>`).join("")}
                        </div>
                    </div>
                    <div class="col-lg-3">
                        <div class="ia-subtitulo">Eventos sugeridos</div>
                        ${(a.sugestoes_eventos || []).map(s => `
                            <div class="sug-item"><i class="bi bi-lightbulb-fill"></i>
                            <div><strong>${esc(s.nome)}</strong><small>${esc(s.categoria)} · ${marcar(s.justificativa)}</small></div></div>`).join("")}
                    </div>
                </div>
                <details class="ia-dados mt-3">
                    <summary><i class="bi bi-shield-check"></i> Transparência: a IA só interpreta. Ver os indicadores calculados enviados para análise.</summary>
                    <pre>${esc(JSON.stringify(r.dados_enviados, null, 2))}</pre>
                </details></div>`;
        } catch (err) {
            fonte.textContent = "indisponível";
            conteudo.innerHTML = '<p class="ia-resumo">Não foi possível gerar a análise agora. Tente novamente.</p>';
        } finally {
            botao.disabled = false;
            const btnMiro = document.getElementById("btnMiro");
            if (btnMiro) btnMiro.disabled = false; // só exporta depois que há análise na tela
        }
    }

    // ---------- Miro: INTELIGÊNCIA → NOVO PLANEJAMENTO ----------
    async function exportarMiro() {
        const botao = document.getElementById("btnMiro");
        const caixa = document.getElementById("miroResultado");
        const original = botao.innerHTML;
        botao.disabled = true;
        botao.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Enviando ao Miro…';
        try {
            const resposta = await fetch(cfg.urlMiro, {
                method: "POST",
                headers: { "X-CSRFToken": obterCsrfToken(), "X-Requested-With": "fetch" },
            });
            const r = await lerJson(resposta);
            if (resposta.status === 401) return irParaLogin(r.login);
            if (!r.ok) throw new Error(r.erro || "Falha ao exportar.");
            caixa.className = "miro-resultado ok";
            caixa.innerHTML = `<i class="bi bi-check-circle-fill"></i>
                <span><strong>${esc(r.titulo)}</strong> criado no quadro com ${r.itens} itens${r.falhas ? ` (${r.falhas} falharam)` : ""}.</span>
                <a href="${esc(r.link)}" target="_blank" rel="noopener" class="btn btn-ia btn-sm"><i class="bi bi-box-arrow-up-right"></i> Abrir no Miro</a>`;
        } catch (err) {
            caixa.className = "miro-resultado erro";
            caixa.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i><span>${esc(err.message)}</span>`;
        } finally {
            caixa.hidden = false;
            botao.disabled = false;
            botao.innerHTML = original;
        }
    }

    // ---------- Início ----------
    renderTudo(JSON.parse(document.getElementById("dados-painel").textContent), true);
    carregarIa(false);
    document.getElementById("btnIa").addEventListener("click", () => carregarIa(true));
    const btnMiro = document.getElementById("btnMiro");
    if (btnMiro) btnMiro.addEventListener("click", exportarMiro);

    setInterval(async () => {
        if (document.hidden) return;
        try { renderTudo(await buscarJson(cfg.urlDados), false); } catch (e) { /* tenta de novo no próximo ciclo */ }
    }, INTERVALO);
})();
