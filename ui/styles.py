import streamlit as st
from config import COR_HEADER


def load_css():
    st.markdown(
        f"""
        <style>
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }}

        .app-header {{
            background-color: {COR_HEADER};
            padding: 20px 32px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .app-header h1 {{
            color: white;
            font-size: 26px;
            font-weight: 800;
            margin: 0;
            letter-spacing: 0.5px;
        }}
        .app-header p {{
            color: #cfe0f0;
            font-size: 14px;
            margin: 4px 0 0 0;
        }}

        .header-row {{
            background: {COR_HEADER};
            border-radius: 10px;
            padding: 0;
            margin-bottom: 10px;
        }}

        .header-row > div {{
            background: {COR_HEADER};
        }}

        .header-row .stForm {{
            min-height: 138px;
            padding: 20px 20px 12px 8px;
            box-sizing: border-box;
        }}

        .header-row .stForm {{
            background: transparent;
            border: 0;
        }}

        .header-row [data-testid="stWidgetLabel"] p {{
            color: #cfe0f0;
            font-size: 12px;
        }}

        .header-row [data-testid="stDateInput"] input {{
            background: #f7f9fc;
            color: #19324d;
        }}

        .header-row button[kind="primaryFormSubmit"] {{
            margin-top: 24px;
            min-height: 40px;
        }}

        .section-title {{
            background: #ffffff;
            border-radius: 10px;
            min-height: 38px;
            padding: 0 14px;
            display: flex;
            align-items: center;
            color: #17324d;
            font-weight: 800;
            font-size: 13px;
            margin: 0 0 8px 0;
        }}

        .section-title p,
        .section-title h3,
        .section-title span {{
            margin: 0;
            padding: 0;
            line-height: 1.2;
        }}

        .top-panel {{
            background: linear-gradient(180deg, rgba(8, 20, 33, 1) 0%, rgba(12, 29, 47, 1) 100%);
            border: 1px solid rgba(73, 128, 191, 0.7);
            border-radius: 16px;
            padding: 12px 14px 8px 14px;
            margin-bottom: 20px;
            box-shadow: 0 10px 26px rgba(0, 0, 0, 0.18);
        }}

        .toolbar-panel {{
            background: rgba(37, 56, 79, 0.7);
            border: 1px solid rgba(146, 182, 219, 0.35);
            border-radius: 10px;
            padding: 8px 12px;
            margin-bottom: 14px;
        }}

        .toolbar-period {{
            color: white;
            text-align: right;
            font-size: 13px;
            padding-top: 4px;
            padding-right: 4px;
        }}

        .toolbar-period strong {{
            font-size: 14px;
        }}

        .content-panel {{
            background: linear-gradient(180deg, rgba(6, 16, 31, 0.96) 0%, rgba(11, 24, 39, 0.96) 100%);
            border: 1px solid rgba(73, 128, 191, 0.55);
            border-radius: 18px;
            padding: 16px 18px 12px 18px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.14);
        }}

        .kpi-card {{
            background: white;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
            text-align: center;
            min-height: 130px;
        }}
        .kpi-card .kpi-title {{
            font-size: 12px;
            font-weight: 700;
            color: #444;
            text-transform: uppercase;
            margin-bottom: 6px;
        }}
        .kpi-card .kpi-value {{
            font-size: 28px;
            font-weight: 800;
            color: {COR_HEADER};
        }}
        .kpi-card .kpi-sub {{
            font-size: 11px;
            color: #888;
            margin-top: 4px;
        }}

        .info-banner {{
            background: #f2f4f7;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
            color: #333;
            margin: 10px 0 18px 0;
        }}

        .chart-box {{
            background: white;
            border-radius: 12px;
            padding: 14px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }}
        .chart-caption {{
            background: #eef2f7;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
            color: #555;
            margin-top: 8px;
        }}

        .post-row {{
            display: flex;
            gap: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            font-size: 13px;
            align-items: center;
        }}
        .post-thumb {{
            width: 42px; height: 42px; border-radius: 6px;
            background: #d7e3ef; flex-shrink: 0;
        }}

        .insight-item {{
            font-size: 13px;
            margin-bottom: 10px;
        }}
        .insight-item b {{ color: {COR_HEADER}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
