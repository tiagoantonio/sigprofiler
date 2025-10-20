# 🧬 DNA Repair Lab – Análise de Assinaturas Mutacionais

Este aplicativo Streamlit permite realizar uma **análise completa de assinaturas mutacionais** a partir de arquivos **VCF** (Variant Call Format).  
Baseado nas ferramentas da família **SigProfiler**, o app automatiza desde a preparação de matrizes até o ajuste de assinaturas COSMIC e a geração de gráficos e relatórios em PDF.

---

## 🚀 Funcionalidades

- Upload de um ou vários arquivos `.vcf`  
- Seleção do genoma de referência (**GRCh37** ou **GRCh38**)  
- Exclusão de grupos de assinaturas mutacionais específicas  
- Ajuste automático de assinaturas COSMIC  
- Geração de matrizes e gráficos
- Exibição direta de PDFs de resultados no navegador  

---

## 🧩 1. Requisitos

Certifique-se de ter instalado:
- Python **3.9+** (idealmente 3.10 ou superior)
- `pip` atualizado (`python -m pip install --upgrade pip`)
- [Git](https://git-scm.com/downloads) (opcional, para clonar o repositório)

---

## 📦 2. Instalação dos pacotes necessários

### Crie e ative um ambiente virtual (recomendado)

```bash
# Criar ambiente
python -m venv venv

# Ativar (Linux/macOS)
source venv/bin/activate

# Ativar (Windows)
venv\Scripts\activate
```

### Instale as dependências

```bash
pip install streamlit SigProfilerMatrixGenerator SigProfilerAssignment sigProfilerPlotting
```

⚠️ **Dica importante:**  
O `SigProfilerMatrixGenerator` baixa automaticamente o genoma de referência (GRCh37/GRCh38) na primeira execução.  
Este processo pode demorar alguns minutos e requer conexão com a internet.

---

## 🧬 3. Estrutura do projeto

```text
dna-repair-lab/
│
├── app.py                  # Código principal (Streamlit)
├── README.md               # Este arquivo
├── tmp/                    # Diretório temporário para resultados
│   └── <projetos>/         # Cada análise criada no app
└── requirements.txt        # (opcional) lista de dependências
```

Você pode criar o `requirements.txt` com:

```bash
pip freeze > requirements.txt
```

---

## ▶️ 4. Executando o app localmente

Dentro da pasta do projeto:

```bash
streamlit run app.py
```

O Streamlit abrirá automaticamente no navegador (ou acesse manualmente):  
👉 [http://localhost:8501](http://localhost:8501)

---

## 🧠 5. Uso do aplicativo

1. **Selecione o genoma** de referência (GRCh37 ou GRCh38)  
2. **(Opcional)** escolha grupos de assinaturas a excluir  
3. **Defina o nome do projeto**  
4. **Envie arquivos .vcf** (um ou vários)  
5. Clique em **🚀 Executar Análise**

O app irá:
- Baixar o genoma se necessário  
- Gerar matrizes mutacionais  
- Ajustar assinaturas COSMIC  
- Criar gráficos e relatórios PDF  
- Exibir os PDFs diretamente na interface  

---

## 🪶 6. Logs e resultados

- Os logs são salvos em:  
  ```
  tmp/<nome_do_projeto>/resultados/analysis.log
  ```
- PDFs e gráficos gerados podem ser baixados diretamente pelo app.  

---

## ⚠️ 7. Possíveis problemas

| Erro / Sintoma | Causa provável | Solução |
|----------------|----------------|----------|
| `Permission denied` em pastas de instalação | Instalação do SigProfiler sem permissão de escrita | Execute novamente em um diretório com permissões (ex: seu diretório home) |
| `genome not found` | Genoma ainda não baixado | O app fará o download automático na primeira execução |
| Falha ao instalar pacotes | Versão antiga do pip ou Python | Atualize com `pip install --upgrade pip` e garanta `python >= 3.9` |

---

## 👨‍🔬 8. Créditos

Desenvolvido por **@tiagoantonio**  
Baseado em:
- [SigProfilerMatrixGenerator](https://github.com/AlexandrovLab/SigProfilerMatrixGenerator)
- [SigProfilerAssignment](https://github.com/AlexandrovLab/SigProfilerAssignment)
- [sigProfilerPlotting](https://github.com/AlexandrovLab/sigProfilerPlotting)
- Framework [Streamlit](https://streamlit.io/)

---

## 💡 Sugestão de melhoria futura

- Cache de genomas compartilhado entre usuários  
- Suporte a outros formatos além de `.vcf`  
- Exportação compacta de resultados (ZIP automático)
