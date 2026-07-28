# 📜 CHANGELOG — Painel de Controle CaPGPq-EFLCH

Todas as alterações notáveis, correções de bugs, novas funcionalidades e melhorias de desempenho do projeto são registradas neste documento com data e hora.

---

## [v0.7.0] — 28/07/2026 19:25

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
  - Resolução definitiva da extração de PDFs compactados (`pdfplumber` + `pypdf`).
  - Implementação de diretiva portátil de autoverificação silenciosa de pacotes na inicialização do aplicativo (`auto_verify_portable_environment`).
  - Correção na raspagem e validação física dos PDFs de Histórico Escolar e Comprovante de Matrícula.
- **Interface e Design System (UNIFESP)**:
  - Padronização de botões para o tema oficial UNIFESP (**Verde Escuro `#174C33`** com hover em **Verde Folha `#82bf24`**).
  - Inclusão do cabeçalho oficial *"Painel de Controle - CAPGPQ - EFLCH"* na tela de login.
  - Ocultação automática do formulário de login do SIIU em gaveta expansível após autenticação.
  - Atualização do rodapé institucional para Versão 0.7 (28/07/2026).

---

## [v0.6.0] — 27/07/2026

### 🛠️ Correções e Ajustes
- Mapeamento da coluna de término do curso excluindo falsos positivos com colunas de prazos de cadastramento.
- Implementação de módulo de conferência de dados com robô em segundo plano para EMTU e SPTrans.
- Adição de botão de atualização direta na planilha para divergências de término de curso.

---

## [v0.5.0] — 21/07/2026

### 🎉 Lançamento da Versão Portátil
- Estruturação do aplicativo em pacote portátil executável offline via `Iniciar_Painel.bat`.
- Integração com Google Sheets API e módulos de automação SIIU.
