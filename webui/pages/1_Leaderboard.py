from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ABS_PATH = Path(__file__).absolute()
PROJECT_PATH = ABS_PATH.parent.parent

# 页面配置
st.set_page_config(page_title="评测结果排行榜", page_icon="🏆", layout="wide")
st.title("🏆 FlashC-Benchmark")

# 读取Excel文件


@st.cache_data  # 缓存数据避免重复加载
def load_data():
    _path = PROJECT_PATH / "databases" / "评测榜单.xlsx"
    _df = pd.read_excel(_path, sheet_name="评测数据", header=1)
    _df = _df.set_index(keys="序号")
    _col_info = {"major": ["模型", "类型", "备注"], "other": []}
    for col in list(_df.columns):
        if col in _col_info["major"]:
            continue
        _col_info["other"].append(col)
    return _df, _col_info


try:
    # 加载数据
    df, col_info = load_data()

    # 侧边栏 - 数据筛选选项
    st.sidebar.header("能力维度")

    # 选择默认排序列
    sort_column = st.sidebar.selectbox("默认排序列", col_info["other"], label_visibility="hidden")

    # 选择排序方式
    sort_ascending = st.sidebar.radio("排序方式", ["降序", "升序"]) == "升序"

    # 图表设置
    st.sidebar.header("图表设置")
    display_count = st.sidebar.slider("显示前N名模型", min_value=3, max_value=min(20, len(df)), value=10)
    chart_type = st.sidebar.radio("图表类型", ["雷达图", "柱状图", "条形图"])

    # 将选中的排序列移到第一列位置
    all_columns = col_info["other"].copy()
    all_columns.remove(sort_column)
    new_column_order = col_info["major"] + [sort_column] + all_columns

    # 4. 按照新的列顺序重新组织DataFrame
    df_reordered = df[new_column_order]

    # 5. 按选择的列和方式排序
    df_sorted = df_reordered.sort_values(by=sort_column, ascending=sort_ascending).reset_index(drop=True)

    # 展示排行榜数据表格
    st.subheader("📊 排行榜数据")
    st.dataframe(df_sorted, use_container_width=True, height=500)

    # 显示数据行数
    st.write(f"共 {len(df)} 条记录")

    # 可视化部分
    st.subheader(f"📈 {sort_column}排行榜")

    # 准备图表数据
    chart_data = df_sorted.head(display_count).copy()

    # 根据用户选择创建不同类型的图表
    if chart_type == "柱状图":
        fig = px.bar(
            chart_data,
            y="模型",
            x=sort_column,
            orientation="h",
            text=sort_column,
            color=sort_column,
            color_continuous_scale="Blues",
            title=f"Top {display_count} 模型 - {sort_column}",
            height=500
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "条形图":
        fig = px.bar(
            chart_data,
            x="模型",
            y=sort_column,
            text=sort_column,
            color=sort_column,
            color_continuous_scale="Greens",
            title=f"Top {display_count} 模型 - {sort_column}",
            height=500
        )
        st.plotly_chart(fig, use_container_width=True)

    elif chart_type == "雷达图":
        # 雷达图需要选择要比较的多个维度
        st.sidebar.subheader("雷达图设置")
        radar_metrics = st.sidebar.multiselect(
            "选择要比较的维度",
            col_info["other"],
            default=[sort_column] + all_columns[:min(7, len(all_columns))]
        )

        if radar_metrics:
            # 准备雷达图数据
            radar_data = chart_data[["模型"] + radar_metrics].set_index("模型")

            fig = go.Figure()

            for model in radar_data.index:
                fig.add_trace(go.Scatterpolar(
                    r=radar_data.loc[model].values,
                    theta=radar_metrics,
                    fill="toself",
                    name=model
                ))

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                    ),
                ),
                showlegend=True,
                title=f"Top {display_count} 模型多维度对比",
                height=600
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("请至少选择一个维度用于雷达图")

    # 额外添加多维度比较图
    if st.checkbox("显示多维度对比", value=True):
        st.subheader("🔍 多维度对比")
        compare_metrics = st.multiselect("选择要比较的维度", col_info["other"], default=[sort_column])
        compare_models = st.multiselect("选择要比较的模型", df_sorted["模型"].tolist(),
                                        default=df_sorted["模型"].head(5).tolist())

        if compare_metrics and compare_models:
            compare_data = df_sorted[df_sorted["模型"].isin(compare_models)]
            fig = px.bar(
                compare_data,
                x="模型",
                y=compare_metrics,
                barmode="group",
                title="模型多维度对比",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

except FileNotFoundError:
    st.error("找不到文件: 评测榜单.xlsx")
except Exception as e:
    st.error(f"加载数据时出错: {str(e)}")
