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
    st.session_state["results_
