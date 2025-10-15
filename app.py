#!/usr/bin/env python3
import os
import sys
import logging
import gzip
import base64
import shutil
from pathlib import Path

import streamlit as st

# ==============================================================
# 🔧 Redirecionamento seguro do SigProfiler para ambiente restrito
# ==============================================================
# --- Forçar diretórios locais ---
SAFE_BASE = Path("tmp")
SAFE_REF = SAFE_BASE / "SigProfiler_safe_refs"
SAFE_REF.mkdir(parents=True, exist_ok=True)

original_makedirs = os.makedirs

def safe_makedirs(path, *args, **kwargs):
    """Redireciona qualquer tentativa de criar pastas em site-packages."""
    try:
        path_str = str(path)
        if "site-packages/SigProfilerMatrixGenerator/references" in path_str:
            rel = Path(path_str.split("SigProfilerMatrixGenerator/references")[-1].lstrip("/"))
            new_path = SAFE_REF / rel
            new_path.parent.mkdir(parents=True, exist_ok=True)
            return original_makedirs(new_path, *args, **kwargs)
        return original_makedirs(path, *args, **kwargs)
    except PermissionError:
        # Em último caso, redireciona tudo para tmp
        new_path = SAFE_REF / Path(str(path)).name
        new_path.parent.mkdir(parents=True, exist_ok=True)
        return original_makedirs(new_path, *args, **kwargs)

os.makedirs = safe_makedirs

# --- Corrige o diretório de trabalho do SigProfiler ---
BASE_TMP = Path("tmp")
CUSTOM_HOME = BASE_TMP / ".sigProfilerHome"
CUSTOM_REFS = BASE_TMP / ".sigProfilerReferences"
CUSTOM_HOME.mkdir(parents=True, exist_ok=True)
CUSTOM_REFS.mkdir(parents=True, exist_ok=True)

os.environ["HOME"] = str(CUSTOM_HOME.resolve())
os.environ["SIGPROFILER_REFERENCES_PATH"] = str(CUSTOM_REFS.resolve())

# --- Ponto crucial ---
# Força o módulo SigProfilerMatrixGenerator a usar nosso diretório local
import SigProfilerMatrixGenerator
SigProfilerMatrixGenerator.__path__ = [str((BASE_TMP / "SigProfilerMatrixGenerator").resolve())]


# ==============================================================
# 📦 Importações principais (após redirecionamento)
# ==============================================================

from SigProfilerMatrixGenerator import install as genInstall
from SigProfilerMatrixGenerator.scripts import SigProfilerMatrixGeneratorFunc as matGen
from SigProfilerAssignment import Analyzer as Analyze
import sigProfilerPlotting as sigPlt


# ---------------------------------------------------------
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
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    logging.info("Logging initialized.")
    return log_file


def ensure_genome_installed(genome_build: str):
    """Instala o genoma localmente, redirecionando referências."""
    genome_path = CUSTOM_REFS / genome_build
    if genome_path.exists():
        st.info(f"✅ Genoma {genome_build} já instalado em {genome_path}")
        return

    st.warning(f"Instalando genoma {genome_build} em {genome_path}...")

    from SigProfilerMatrixGenerator import install as genInstall

    # Instala localmente, sem tocar em /site-packages
    genInstall.install(genome_build, rsync=False, bash=True)

    # Move qualquer dado baixado acidentalmente para dentro do tmp
    pkg_refs = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages" / "SigProfilerMatrixGenerator" / "references"
    if pkg_refs.exists():
        shutil.copytree(pkg_refs, CUSTOM_REFS, dirs_exist_ok=True)
        shutil.rmtree(pkg_refs, ignore_errors=True)

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
    for ctx in contexts:
        input_path = Path(base_dir) / f"output/SBS/{project}.SBS{ctx}.all"
        if not input_path.exists():
            logging.warning(f"Matriz SBS{ctx} não encontrada: {input_path}")
            continue
        logging.info(f"Plotando SBS{ctx}...")
        sigPlt.plotSBS(
            str(input_path),
            output_path=str(base_dir),
            project=project,
            plot_type=str(ctx),
            percentage=False,
        )
        
# --- Função para salvar sessão ---
def save_results_session(project_name, results_dir):
    st.session_state["project_name"] = project_name
    st.session_state["results_dir"] = str(results_dir)

    
# def validate_vcf(file) -> bool:
#     """Valida se o arquivo parece ser um VCF, de forma tolerante."""
#     if not file.name.lower().endswith(".vcf"):
#         return False
#     try:
#         # Lê apenas as primeiras linhas
#         head = file.read(4096).decode("utf-8", errors="ignore")
#         file.seek(0)
#         # Critérios relaxados
#         #valid = any(tag in head for tag in ["##fileformat=VCF", "#CHROM", "CHROM\tPOS\tID"])
#         return valid
#     except Exception:
#         file.seek(0)
#         return False

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
                               "APOBEC_signatures",
                               "Tobacco_signatures",
                               "UV_signatures",
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


uploaded_files = st.file_uploader(
    "📤 Envie seus arquivos .vcf (um ou vários):",
    type=["vcf"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} arquivo(s) carregado(s).")

    # Validar formato
    # valid_files = [f for f in uploaded_files if validate_vcf(f)]
    valid_files = [f for f in uploaded_files]
    # if len(valid_files) < len(uploaded_files):
        # st.warning("Alguns arquivos não parecem estar em formato VCF válido e foram ignorados.")
else:
    st.info("Aguardando upload de arquivos .vcf...")


# ---------------------------------------------------------
# Botão para executar o pipeline
# ---------------------------------------------------------
# --- Forçar diretórios com permissão ---


custom_genome_dir = Path("tmp/genomes")
custom_genome_dir.mkdir(parents=True, exist_ok=True)

base_dir = Path("tmp")
project_root = base_dir / project_name
project_dir = project_root / "vcfs"
output_dir = project_root / "resultados"

project_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)


if st.button("🚀 Executar Análise"):
    if not uploaded_files:
        st.error("Envie pelo menos um arquivo .vcf antes de iniciar.")
        st.stop()

    with st.spinner("Executando análise... isso pode levar alguns minutos."):
        try:
            
            # Limpa diretórios antigos para este projeto
            if project_root.exists():
                shutil.rmtree(project_root)
                project_dir.mkdir(parents=True, exist_ok=True)
                output_dir.mkdir(parents=True, exist_ok=True)
            # Estrutura esperada pelo SigProfiler:

            # Salvar arquivos enviados
            for file in valid_files:
                target_path = project_dir / file.name
                if file.name.endswith(".gz"):
                     with gzip.open(file, "rb") as f_in, open(target_path.with_suffix(""), "wb") as f_out:
                        f_out.write(f_in.read())
                else:
                    with open(target_path, "wb") as f_out:
                        f_out.write(file.read())
                logging.info(f"Arquivo salvo em {target_path}")

#                # Verificar o que realmente existe
#                st.markdown("### 📂 Estrutura de entrada:")
#                for path in project_root.rglob("*"):
#                    st.write("-", path.relative_to(base_dir))

            # Garantir que há pelo menos um VCF
            vcfs = list(project_dir.glob("*.vcf"))
            if not vcfs:
                st.error("Nenhum arquivo VCF foi encontrado após o upload.")
                st.stop()

            # Setup logging
            log_path = setup_logging(output_dir)
            ensure_genome_installed(genome)

            # 🔹 Gerar matrizes
            st.info("Gerando matrizes...")
            SigProfilerMatrixGenerator.__path__ = [str((BASE_TMP / "SigProfilerMatrixGenerator").resolve())]
            os.environ["SIGPROFILER_REFERENCES_PATH"] = str(CUSTOM_REFS.resolve())
            generate_matrices(project_name, genome, str(project_dir))

            # 🔹 Ajustar assinaturas
            st.info("Ajustando assinaturas COSMIC...")
            fit_signatures(str(project_dir), str(output_dir), genome, exclude_groups)

            # 🔹 Plotar contextos
            st.info("Gerando gráficos de contextos...")
            plot_contexts(str(project_dir), project_name, contexts)
            
        except Exception as e:
            st.error(f"Erro durante a execução: {e}")
            logging.exception("Erro no pipeline.")
            
# 🔹 Procurar resultados
fit_results = list(output_dir.rglob("*"))
other_results = list(project_dir.rglob("*"))
other_files = [f for f in other_results if f.suffix == ".pdf"]
fit_files = [f for f in fit_results if f.suffix == ".pdf"]
pdf_files = fit_files + other_files
                
st.session_state["results_dir"] = str(output_dir)
st.session_state["project_name"] = project_name
                    
if pdf_files:
    st.success(f"✅ Showing results for: {project_name}")
    selected_pdf = st.selectbox("Choose a PDF to view:", pdf_files)
    with open(selected_pdf, "rb") as f:
        pdf_bytes = f.read()
        b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="800px"></iframe>', unsafe_allow_html=True)

        st.success("✅ Análise concluída com sucesso!")
else:
    st.error("Nenhum resultado foi gerado.")


# ---------------------------------------------------------
# Rodapé
# ---------------------------------------------------------
st.markdown("---")
st.caption("Desenvolvido por @tiagoantonio • Baseado em SigProfiler • Streamlit + boas práticas 🧬")
