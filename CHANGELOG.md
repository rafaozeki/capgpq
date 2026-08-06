# 📜 CHANGELOG COMPLETO — Painel de Controle CaPGPq-EFLCH

Todas as alterações notáveis, correções de bugs, novas funcionalidades e marcos históricos do projeto **Painel de Controle CaPGPq-EFLCH** estão registrados neste documento em ordem cronológica reversa.

## [v0.9.5] — 06/08/2026 (Horário: 19:35)

### 🚀 Otimização de Performance e Carregamento Sob Demanda
- **Eliminação do Carregamento Automático Lento**:
  - As páginas do *Painel de Controle* e de *Módulos de Demandas* não realizam mais chamadas HTTP automáticas ao Google Sheets ao serem abertas, reduzindo o tempo de carregamento inicial para **0 segundos (carregamento instantâneo)**.
- **Fluxo de Filtro Primeiro + Consulta Sob Demanda**:
  - Exibição inicial dos seletores de filtro. O carregamento de dados é disparado exclusivamente ao clicar no botão **`🔍 Consultar & Filtrar Planilhas`**.
- **Cache de Sessão Inteligente (`st.session_state`)**:
  - Armazenamento em memória dos dados baixados para navegação ultrarrápida entre filtros.
  - Inclusão do botão **`🔄 Atualizar Dados`** para forçar a busca de novos registros no Google Drive quando desejado.

---

## [v0.9.0] — 06/08/2026 (Horário: 19:28)

### ⚡ Painel de Controle Sintético e Central de Acesso Rápido
- **Remoção de Listas Longas de Alunos**:
  - Eliminação da lista extensa de solicitações individuais no *Painel de Controle*, mantendo a página ultra leve, limpa e focada em visão situacional.
- **Tabela Resumo Comparativa das Demandas**:
  - Exibição de tabela sintética comparando todos os módulos e seus totais de pendências (*Expiradas*, *Urgentes*, *Médio Prazo*, *Regular*).
- **Grid de Lançamento de Módulos (2 Colunas)**:
  - Criação de cartões sintéticos enxutos por atividade com indicadores numéricos de status.
  - Botão **`🌐 Planilha no Google`** (Link direto externo para o Google Sheets em 1 clique).
  - Botão **`🚀 Ir para [Módulo]`** (Navegação direta em 1 clique para a página detalhada do módulo).

---

## [v0.8.2] — 06/08/2026 (Horário: 19:26)

### 📅 Formatação de Data em Padrão Brasileiro (DD/MM/YYYY)
- **Formatação de Seleção de Período Customizado**:
  - Definição do parâmetro `format="DD/MM/YYYY"` em todos os seletores de data (`st.date_input`) do sistema.
  - Exibição estrita no padrão brasileiro **dia/mês/ano** (ex: `28/07/2026`).

---

## [v0.8.1] — 06/08/2026 (Horário: 19:20)

### 🎨 Organização Visual por Tópicos de Atividades
- **Agrupamento por Tópicos**:
  - Reorganização da lista de atividades do *Painel de Controle* em tópicos separados por nome de atividade/módulo (`📂 Tópico: Nome da Atividade`).
- **Acesso Direto à Planilha por Tópico**:
  - Inclusão do botão **`🌐 Acessar Planilha ([Atividade])`** diretamente abaixo do cabeçalho de cada tópico de atividade para acesso direto ao Google Sheets em 1 clique.

---

## [v0.8.0] — 06/08/2026 (Horário: 19:15)

### 🚀 Novas Funcionalidades e Reorganização do Menu
- **Reorganização do Menu Lateral**:
  - Alteração da seção do menu lateral de *"Painel de Controle"* para **"Menu"**.
  - Criação do novo botão de acesso rápido **`📋 Painel de Controle`** no topo da barra lateral.
- **Central Unificada do Painel de Controle (`show_control_panel`)**:
  - Consolidação global de todas as atividades disponíveis para execução em todas as planilhas monitoradas do sistema.
  - Filtros simultâneos globais por *Módulo/Demanda*, *Período de Solicitação*, *Tipo de Solicitação* e *Data para Execução / Urgência*.
  - Indicadores numéricos globais de atividades *Expiradas*, *A Vencer (0 a 7 dias)* e *Médio Prazo (8 a 30 dias)*.
  - Exportação de relatório unificado em CSV/Excel e impressão direta em layout A4 HTML.
  - Exibição de cartões expansíveis unificados com tags visuais de urgência (`🔴 EXPIRADA`, `🚨 URGENTE`, `⚠️ MÉDIO PRAZO`, `🟢 REGULAR`) e edição direta em 1 clique.

---

## [v0.7.0] — 28/07/2026 (Horário: 19:25)

### 🚀 Novas Funcionalidades e Melhorias
- **Painel Executivo e Previsão de Demandas**:
  - Implementação de filtros simultâneos combinados (*Período de Solicitação*, *Tipo de Solicitação* e *Data para Execução / Urgência*).
  - Adição de estatísticas e métricas com separação estrita de demandas *Expiradas*, *A Vencer (0 a 7 dias)* e *Médio Prazo (8 a 30 dias)*.
  - Adição do recurso de exportação de relatório completo em formato CSV / Excel contendo 100% dos dados da planilha e cálculo de urgência.
  - Implementação do botão **🖨️ Imprimir / Baixar Relatório (HTML)** gerando documento formatado em A4 Landscape com disparo automático de impressão nativa (`window.print()`).
- **Controle de Processos SEI**:
  - Renomeação do rótulo *"Endereço de e-mail"* para **"Processo recebido por"**.
  - Mapeamento e exibição completa dos campos: *Tipo de solicitação*, *Unidade*, *Situação (triagem)*, *Nº do Processo*, *Data para Execução*, *Observações*, *Recebido em* e *Data da demanda*.
  - Ordenação estrita das informações dentro dos cards expansíveis.
- **Automação SIIU e Leitura de PDF**:
  - Resolução definitiva da extração de PDFs compactados por zlib (`pdfplumber` + `pypdf`).
  - Implementação de diretiva portátil de autoverificação silenciosa de pacotes na inicialização do aplicativo (`auto_verify_portable_environment`).
  - Correção na raspagem e validação física dos PDFs de Histórico Escolar e Comprovante de Matrícula.
- **Interface e Design System (UNIFESP)**:
  - Padronização de botões para o tema oficial UNIFESP (**Verde Escuro `#174C33`** com hover em **Verde Folha `#82bf24`**).
  - Inclusão do cabeçalho oficial *"Painel de Controle - CAPGPQ - EFLCH"* na tela de login.
  - Ocultação automática do formulário de login do SIIU em gaveta expansível após autenticação.
  - Atualização do rodapé institucional para Versão 0.7 (28/07/2026).

---

## [v0.6.0] — 27/07/2026 a 28/07/2026 (Horário: 02:30)

### 🛠️ Correções e Diagnóstico de PDF
- **Debug de Leitura de PDF em Tempo Real**:
  - Criação da aba expansível `🐞 Debug da Leitura de PDF` no painel, exibindo caminho do arquivo, tamanho em bytes, status de existência, texto bruto lido e campos JSON extraídos.
- **Leitura Nativa de PDF com pdfplumber e pypdf**:
  - Correção do problema onde PDFs retornavam vazio ("Nenhum texto pôde ser lido") devido à descompactação de streams zlib (`/FlateDecode`).
  - Instalação e verificação dos pacotes no ambiente Python do aplicativo portátil.
- **Assistentes de Conferência de Transporte (EMTU e SPTrans)**:
  - Resolução de mapeamentos de colunas da planilha de requisição de passe escolar.
  - Correção de falsos positivos na captura da data de término do curso (diferenciando de avisos de prazo de cadastramento).
  - Botão de atualização da planilha do Google em 1 clique para correção de divergências.
- **Gerenciamento de Senha**:
  - Alteração da senha de acesso do sistema para `"cafezinho"`.

---

## [v0.5.0] — 21/07/2026 (Horário: 15:00)

### 📦 Lançamento da Versão Portátil Offline
- **Pacote Autônomo (Painel_CAPGPQ_Portatil)**:
  - Criação da estrutura de pastas portátil contendo Python 3.11 embarcado e navegadores Playwright pré-instalados.
  - Criação do inicializador rápido `Iniciar_Painel.bat` para execução com 2 cliques sem necessidade de instalar dependências no computador do usuário.
  - Isolamento de variáveis de ambiente, pastas de downloads locais e logs de execução.

---

## [v0.4.0] — 15/07/2026

### 🤖 Robô de Raspagem Avançada do SIIU (Playwright)
- **Extração Automatizada de Alunos**:
  - Desenvolvimento do extrator assíncrono Playwright (`siiu_extractor.py`) para os módulos *Matrícula Única* e *Sistema de Gestão da Pós-Graduação*.
  - Suporte ao fluxo de busca por Nome, CPF e Matrícula (RA) com resolução de múltiplos vínculos discentes.
- **Mapeamento por Regex e Leitura de Histórico**:
  - Raspagem automatizada dos dados pessoais e acadêmicos: *Nome, CPF, RG, Órgão Emissor, UF, Sexo, Data de Nascimento, Naturalidade, Forma de Ingresso, Ano de Ingresso, Programa, Nível, Situação, Tese, Orientador, Créditos Aprovados* e *Tabela Completa de Disciplinas Cursadas*.
- **Download e Visualização de PDF**:
  - Captura automática dos PDFs de *Histórico Acadêmico* e *Comprovante de Matrícula* via requisições autenticadas de contexto (`page.context.request`).
  - Abertura de abas visíveis no Chromium para acompanhamento em tempo real pelo usuário.

---

## [v0.3.0] — 10/07/2026

### 📊 Integração com Google Sheets e Módulo Polare
- **Conexão com Google Drive API**:
  - Leitura e gravação em tempo real de planilhas do Google Sheets com Service Account e escopos OAuth2.
  - Atualização direta de células da planilha (`update_sheet_cell`) a partir da interface do painel via botões popover `✏️`.
- **Módulo Polare - Lançamento de Atividades**:
  - Leitura automatizada da planilha de nomenclaturas do Polare (`POLARE - ATIVIDADES`).
  - Gerador de textos padronizados e cópia instantânea para lançamentos de carga horária e subatividades.
- **Painéis Dinâmicos de Demandas**:
  - Suporte a monitoramento de planilhas personalizáveis (Diplomas, Declarações de Conclusão, EMTU, SPTrans, Liberação de Usuário Externo SEI, Bancas de Defesa).

---

## [v0.2.0] — 05/07/2026

### 🔒 Controle de Acesso e Módulo de Históricos
- **Módulo Análise de Históricos Acadêmicos**:
  - Interface dedicada para busca direta de alunos do SIIU e conferência de pendências cadastrais.
  - Armazenamento temporário de credenciais na memória da sessão (`st.session_state`).
- **Segurança de Acesso**:
  - Sistema de login por senha para restrição de acesso ao painel interno.

---

## [v0.1.0] — 01/07/2026

### 🏛️ Arquitetura Inicial do Sistema e Design System
- **Desenvolvimento da Aplicação Base (Streamlit)**:
  - Criação da estrutura de código em Python usando o framework Streamlit.
  - Implementação da navegação por menu lateral interativo (`st.sidebar`).
- **Design System Institucional UNIFESP**:
  - Customização CSS avançada com a tipografia oficial *Merriweather*.
  - Paleta de cores institucional com destaque para o **Verde Escuro `#174C33`** e **Verde Folha `#82bf24`**.
