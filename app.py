#!/usr/bin/env python3
import os
import sys
import logging
import gzip
import base64
import shutil
from pathlib import Path

import streamlit as st

# --- IMPORTAÇÕES DA BIBLIOTECA SIGPROFILER ---
from SigProfilerMatrixGenerator import install as genInstall
from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
from SigProfilerAssignment import Analyzer as Analyze
import sigProfilerPlotting as sigPlt

# =========================================================================
# === SOLUÇÃO CRÍTICA PARA ERRO DE PERMISSÃO (Errno 13) ===
# =========================================================================

# 1. Define o diretório temporário para todos os dados do aplicativo
base_dir = Path("tmp") 
base_dir.mkdir(parents=True, exist_ok=True)

# 2. Define onde os arquivos de referência serão gravados (o caminho que a biblioteca usa internamente)
custom_refs_dir = base_dir / "SigProfilerMatrixGenerator" / "references" 
custom_refs_dir.mkdir(parents=True, exist_ok=True)

# 3. FORÇA A VARIÁVEL DE AMBIENTE (necessária para algumas partes)
os.environ["SIGPROFILER_REFERENCES_PATH"] = str(custom_refs_dir.resolve())

# 4. MODIFICA O CAMINHO INTERNO DA BIBLIOTECA APÓS A IMPORTAÇÃO (CRÍTICO!)
# Isso garante que a biblioteca use o caminho personalizado, resolvendo o 'Permission denied'.
try:
    from SigProfilerMatrixGenerator.references import REFERENCE_PATH
    # Assumindo que SigProfilerMatrixGenerator é uma biblioteca de terceiros
    # Essa linha substitui o caminho interno padrão da biblioteca
    SigProfilerMatrixGenerator.references.REFERENCE_PATH = str(custom_refs_dir.resolve())
    logging.info(f"Caminho interno do SigProfiler forçado para: {SigProfilerMatrixGenerator.references.REFERENCE_PATH}")
except ImportError:
    # Captura se o módulo de references não for importável diretamente
    logging.warning("Não foi possível acessar e forçar SigProfilerMatrixGenerator.references.REFERENCE_PATH. A variável de ambiente será usada como fallback.")

# =========================================================================
# =========================================================================


# Configuração inicial do Streamlit
# ---------------------------------------------------------
st.set_page_config(
    page_title="DNA Repair Lab: Assinaturas mutacionais",
    layout="wide",
    page_icon="🧬"
)

st.title("🧬 DNA Repair Lab: Assinaturas mutacionais")
st.markdown("""
Este aplicativo realiza uma análise completa de assinaturas mutacionais a partir de arquivos **VCF**:
1. Escolha o genoma de referência 
2. Exclua grupos de assinaturas 
3. Ajusta assinaturas COSMIC  
4. Gera gráficos e relatórios em PDF  
""")


# ---------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------
def setup_logging(output_dir):
    log_file = Path(output_dir) / "analysis.log"
    # Limpa handlers antigos do Streamlit
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    logging.info("Logging initialized.")
    logging.info(f"Caminho de referência SigProfiler atual: {os.environ.get('SIGPROFILER_REFERENCES_PATH')}")
    # Nota: Em ambientes teimosos, a linha de log acima pode ainda mostrar o caminho de site-packages,
    # mas a modificação direta deve ter resolvido o problema de escrita.
    return log_file


def ensure_genome_installed(genome_build: str):
    """Instala o genoma localmente, usando o caminho modificado internamente."""
    logging.info(f"Tentando instalar o genoma {genome_build} no caminho forçado.")
    # bash=False é mais seguro em ambientes virtuais/Streamlit
    genInstall.install(genome_build, rsync=False, bash=False) 
    st.success(f"Genoma {genome_build} instalado localmente com sucesso!")

def generate_matrices(project, genome_build, input_dir):
    logging.info(f"Gerando matrizes para {input_dir}...")
    return matGen.SigProfilerMatrixGeneratorFunc(
        project,
        genome_build,
        input_dir,
        plot=True,
        exome=False
    )


def fit_signatures(input_dir, output_dir, genome_build, exclude_groups, cosmic_version="3.4"):
    logging.info("Iniciando ajuste de assinaturas COSMIC...")
    Analyze.cosmic_fit(
        samples=input_dir,
        output=output_dir,
        input_type="vcf",
        context_type="96",
        genome_build=genome_build,
        exclude_signature_subgroups=exclude_groups,
        cosmic_version=cosmic_version,
    )
    logging.info("Ajuste de assinaturas completo.")


def plot_contexts(base_dir, project, contexts):
    # base_dir é Path("tmp")
    for ctx in contexts:
        # Caminho onde a matriz foi criada
        input_path = Path(base_dir) / project / f"output/SBS/{project}.SBS{ctx}.all" 
        if not input_path.exists():
            logging.warning(f"Matriz SBS{ctx} não encontrada: {input_path}")
            continue
        logging.info(f"Plotando SBS{ctx}...")
        
        # O sigPlt.plotSBS espera o diretório onde o 'output' será criado
        sigPlt.plotSBS(
            str(input_path),
            output_path=str(Path(base_dir) / project), # Diretório de saída, ex: tmp/meu_projeto/
            project=project,
            plot_type=str(ctx),
            percentage=False,
        )
        
# --- Função para salvar sessão ---
def save_results_session(project_name, results_dir):
    st.session_state["project_name"] = project_name
    st.session_state["results_dir"] = str(results_dir)

# ---------------------------------------------------------
# Interface Streamlit
# ---------------------------------------------------------
# --- Sessão ---
if "project_name" not in st.session_state:
    st.session_state["project_name"] = None
if "results_dir" not in st.session_state:
    st.session_state["results_dir"] = None

    
with st.sidebar:
    st.header("⚙️ Configurações da Análise")

    genome = st.selectbox("Genoma de Referência", ["GRCh37", "GRCh38"])
    exclude_groups = st.multiselect(
        "Excluir grupos de assinaturas",
        ["APOBEC_signatures", "UV_signatures", "Tobacco_signatures", "MMR_signatures", "MMR_deficiency_signatures","POL_deficiency_signatures",
                                 "HR_deficiency_signatures" ,
                                 "BER_deficiency_signatures",
                                 "Chemotherapy_signatures",
                                 "Immunosuppressants_signatures"
                                 "Treatment_signatures"
                                 "AA_signatures",
                                 "Colibactin_signatures",
                                 "Artifact_signatures",
                                 "Lymphoid_signatures"]
    )
    contexts = st.multiselect(
        "Contextos a plotar",
        [6, 96, 288, 1536],
        default=[96]
    )

    project_name = st.text_input("Nome do Projeto", "meu_projeto")


# --- Diretórios do Projeto (Definição dinâmica) ---
# Garante que project_name atualize os paths a cada execução
project_root = base_dir / project_name
project_dir = project_root / "vcfs"
output_dir = project_root / "resultados"

project_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)


uploaded_files = st.file_uploader(
    "📤 Envie seus arquivos .vcf (um ou vários):",
    type=["vcf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} arquivo(s) carregado(s).")
    valid_files = [f for f in uploaded_files]
else:
    st.info("Aguardando upload de arquivos .vcf...")


# ---------------------------------------------------------
# Botão para executar o pipeline
# ---------------------------------------------------------

if st.button("🚀 Executar Análise"):
    if not uploaded_files:
        st.error("Envie pelo menos um arquivo .vcf antes de iniciar.")
        st.stop()

    with st.spinner("Executando análise... isso pode levar alguns minutos."):
        try:
            
            # Limpa diretórios antigos para este projeto e recria
            if project_root.exists():
                shutil.rmtree(project_root)
                project_dir.mkdir(parents=True, exist_ok=True)
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Salvar arquivos enviados
            for file in valid_files:
                target_path = project_dir / file.name
                if file.name.endswith(".gz"):
                    uncompressed_name = target_path.with_suffix("")
                    with gzip.open(file, "rb") as f_in, open(uncompressed_name, "wb") as f_out:
                        f_out.write(f_in.read())
                    logging.info(f"Arquivo (descompactado) salvo em {uncompressed_name}")
                else:
                    with open(target_path, "wb") as f_out:
                        f_out.write(file.read())
                    logging.info(f"Arquivo salvo em {target_path}")


            # Garantir que há pelo menos um VCF (após potencial descompactação)
            vcfs = list(project_dir.glob("*.vcf"))
            if not vcfs:
                st.error("Nenhum arquivo VCF foi encontrado após o upload.")
                st.stop()

            # Setup logging
            log_path = setup_logging(output_dir)
            
            # 🔹 Instalar Genoma (usará o caminho interno modificado)
            st.info("Verificando/Instalando genoma de referência...")
            ensure_genome_installed(genome)

            # 🔹 Gerar matrizes
            st.info("Gerando matrizes...")
            generate_matrices(project_name, genome, str(project_dir))

            # 🔹 Ajustar assinaturas
            st.info("Ajustando assinaturas COSMIC...")
            fit_signatures(str(project_dir), str(output_dir), genome, exclude_groups)

            # 🔹 Plotar contextos
            st.info("Gerando gráficos de contextos...")
            plot_contexts(str(base_dir), project_name, contexts) 
            
            # Salva o estado da sessão
            st.session_state["results_dir"] = str(output_dir)
            st.session_state["project_name"] = project_name
            
        except Exception as e:
            st.error(f"Erro durante a execução: {e}")
            logging.exception("Erro no pipeline.")
            
# 🔹 Procurar resultados
fit_results = list(output_dir.rglob("*.pdf"))
plot_results = list(project_root.rglob("*.pdf"))
pdf_files = fit_results + plot_results

if pdf_files:
    # Remove duplicatas se houver (embora seja improvável) e ordena
    pdf_files = sorted(list(set(pdf_files)), key=lambda x: x.name)
    
    st.success(f"✅ Análise concluída com sucesso! Resultados para: {project_name}")
    selected_pdf = st.selectbox("Escolha um PDF para visualizar:", pdf_files, format_func=lambda x: x.name)
    
    with open(selected_pdf, "rb") as f:
        pdf_bytes = f.read()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="800px"></iframe>', unsafe_allow_html=True)
else:
    if st.session_state["project_name"] and st.session_state["results_dir"]:
         st.warning("Nenhum resultado PDF foi encontrado no diretório após a execução.")
    else:
         st.info("Aguardando execução da análise...")


# ---------------------------------------------------------
# Rodapé
# ---------------------------------------------------------
st.markdown("---")
st.caption("Desenvolvido por @tiagoantonio • Baseado em SigProfiler • Streamlit + boas práticas 🧬")
