# 📜 CHANGELOG COMPLETO — Painel de Controle CaPGPq-EFLCH

Todas as alterações notáveis, correções de bugs, novas funcionalidades e marcos históricos do projeto **Painel de Controle CaPGPq-EFLCH** estão registrados neste documento em ordem cronológica reversa.

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
