# Decisões Técnicas — Shopping Pulse

> Registre decisões aprovadas pela equipe. Diferencie decisões confirmadas de propostas.

## Contexto do projeto
Plataforma para divulgar e validar o interesse por eventos de shopping, coletar interações dos visitantes e oferecer indicadores à administração.

## Decisões identificadas na implementação inicial
| ID | Decisão | Situação | Justificativa |
|---|---|---|---|
| D-001 | Utilizar Django no backend | Implementada | Estrutura atual do projeto |
| D-002 | Separar responsabilidades em módulos de eventos, participação, dashboard e inteligência | Implementada | Organização do código |
| D-003 | Disponibilizar uma experiência web para visitantes e administração | Implementada inicialmente | Facilitar acesso e demonstração |
| D-004 | Usar SQLite como banco de dados do MVP, com Django ORM e migrations | Aprovada em 2026-11-13 | Simplicidade de configuração e persistência entre reinícios (ver P-001) |

### D-004 — Usar SQLite como banco de dados do MVP
- **Data:** 2026-11-13
- **Responsáveis:** solicitante do projeto (aprovação informada na sessão de trabalho)
- **Status:** aprovada
- **Contexto:** os eventos e interações ficam em memória e se perdem ao reiniciar o servidor. A situação atual exige maior persistência dos dados.
- **Alternativas consideradas:** manter dados em memória ou JSON (proposta original do `CLAUDE.md`, revisada); usar outro banco de dados (fora do escopo do MVP).
- **Decisão:** usar SQLite com `DATABASES` do Django, modelos e migrations versionadas. O arquivo `db.sqlite3` fica fora do Git.
- **Justificativa:** banco de arquivo único, sem servidor separado, suficiente para o MVP e fácil de demonstrar.
- **Consequências:** o `CLAUDE.md` foi atualizado para refletir esta decisão. A migração dos dados de demonstração de memória/JSON para o banco ainda precisa ser implementada (Etapa 2 e 3). Não há ainda controle de concorrência para vários processos.
- **Referência:** pendente (sem commit ainda).

## Propostas pendentes de aprovação
| ID | Proposta | Situação | Critério para decisão |
|---|---|---|---|
| P-001 | Usar SQLite no MVP | Aprovada → D-004 | Simplicidade de configuração e persistência |
| P-002 | Usar autenticação e permissões nativas do Django | Em avaliação | Proteção das operações administrativas |
| P-003 | Priorizar o épico de descoberta e engajamento | Em avaliação | Entrega demonstrável de ponta a ponta |
| P-004 | Manter BI determinístico e usar IA para interpretações | Em avaliação | Confiabilidade e explicabilidade dos indicadores |

## Modelo para registrar novas decisões
### D-XXX — Título da decisão
- **Data:** AAAA-MM-DD
- **Responsáveis:** nomes
- **Status:** proposta / aprovada / substituída
- **Contexto:** problema ou necessidade
- **Alternativas consideradas:** opções avaliadas
- **Decisão:** o que foi escolhido
- **Justificativa:** por que foi escolhido
- **Consequências:** impactos, riscos e limitações
- **Referência:** issue, PR ou commit

## Regras de manutenção
- Não transformar sugestões em decisões aprovadas sem confirmação da equipe.
- Ao substituir uma decisão, registrar o motivo e a nova referência.
- Não armazenar credenciais, tokens ou dados pessoais desnecessários.
