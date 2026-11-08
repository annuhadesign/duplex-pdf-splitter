from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_component = components.declare_component('litnus_text_export_2_0', path=str(Path(__file__).parent.resolve()))


def render_text_export(estimate, invoice, filename, key):
    selected = st.session_state.get(key, 'estimate')
    value = _component(estimate=estimate, invoice=invoice, filename=filename,
                       selected=selected, key=key, default='estimate')
    return value if value in ('estimate', 'invoice') else 'estimate'
