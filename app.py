import streamlit as st

st.set_page_config(
    page_title="CCMORPH",
    page_icon="tools/img/icon.png",
    layout="centered",   #centered or wide
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/Baltic-Coastal-Monitoring-Team/CMORPH/blob/main/README.md',
        'Report a bug': "mailto:jakub.sledziowski@usz.edu.pl",
        'About': ("**CMORPH** is an open-source app for coastal morphology analysis.\n"
                 "**Authors:** Śledziowski Jakub, Witold Maćków, Andrzej Łysko, Terefenko Paweł, Giza Andrzej, Kamran Tanwari / Baltic Coastal Monitoring Team")
    }
)

from generator import generator_ui, generator_results, input_data_viewer, get_base_path_from_config
from finder import finder_ui
from analyzer import analyzer_ui
from lines import lines_ui
from stats import stats_ui

st.sidebar.image("tools/img/cmorph-logo.png")


page = st.sidebar.radio("Select step", ["Generator", "Finder", "Analyzer", "Lines", "Stats"])

if page == "Generator":
    subpage = st.sidebar.radio("Generator:", ["Config", "Results", "Input data"])
    if subpage == "Config":
        generator_ui()
    elif subpage == "Results":
        generator_results()
    elif subpage == "Input data":
        base_path = get_base_path_from_config()
        if base_path:
            input_data_viewer(base_path)
        else:
            st.error("The input data cannot be loaded. Incorrect configuration.")

elif page == "Finder":
    finder_ui()

elif page == "Analyzer":
    analyzer_ui()

elif page == "Lines":
    lines_ui()

elif page == "Stats":
    stats_ui()


