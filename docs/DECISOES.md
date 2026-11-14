# Decisões Técnicas — ShoppDash

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
| D-005 | Renomear o produto para ShoppDash (shopping + Rapidash, nome do grupo no evento) e adotar a paleta do ícone do app (âmbar, laranja e café) | Aprovada em 2026-11-14 | Identidade do grupo no Hackathon; ícone e imagem do cabeçalho fornecidos pela equipe. A pasta e os nomes técnicos (`shopping-pulse`, classes `btn-pulse`, `templatetags/pulse`) foram mantidos |
| D-006 | Usar autenticação e permissões nativas do Django para a área administrativa | Aprovada em 2026-11-14 | Proteção das operações administrativas com menos código próprio (ver P-002) |

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

### D-006 — Usar autenticação e permissões nativas do Django para a área administrativa
- **Data:** 2026-11-14
- **Responsáveis:** equipe (aprovação informada pelo solicitante na sessão de trabalho)
- **Status:** aprovada
- **Contexto:** as operações administrativas (painel, eventos, QR Code, simulação, reinício, análise da IA e exportação) precisam de proteção.
- **Alternativas consideradas:** mecanismo de acesso próprio, fora do `django.contrib.auth` (não detalhado na proposta P-002).
- **Decisão:** administradores são usuários do Django com `is_staff=True`, criados por `python manage.py definir_admin`. O login usa `authenticate()`/`login()`, com sessões no banco. Visitantes não acessam o painel. Há limite de tentativas de login por IP.
- **Justificativa:** recursos nativos do Django, sem dependência nova e sem código de autenticação próprio, conforme as regras do `CLAUDE.md`.
- **Consequências:** é preciso criar o administrador em cada banco (`definir_admin`). O limite de tentativas por IP é simples e não substitui proteção de produção.
- **Referência:** `5345b35` (implementação, 13 testes de acesso passando).

## Propostas pendentes de aprovação
| ID | Proposta | Situação | Critério para decisão |
|---|---|---|---|
| P-001 | Usar SQLite no MVP | Aprovada → D-004 | Simplicidade de configuração e persistência |
| P-002 | Usar autenticação e permissões nativas do Django | Aprovada → D-006 | Proteção das operações administrativas |
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
