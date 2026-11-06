                if len(yearly):
                    year_cols = st.columns(min(len(yearly), 5))
                    for idx, (year, group) in enumerate(yearly):
                        yw = int((group["Type"] == "Target Hit 🟢").sum())
                        yl = int((group["Type"] == "SL Hit 🔴").sum())
                        total = yw + yl
                        yr = yw / total * 100 if total else 0
                        year_cols[idx % len(year_cols)].metric(str(year), f"{yr:.1f}% win", f"{yw}W / {yl}L · {group['PnL (%)'].sum():+.1f}%")
                if not closed.empty:
                    curve = closed[["Exit Date", "Portfolio (₹)"]].copy()
                    curve["Exit Date"] = pd.to_datetime(curve["Exit Date"])
                    fig = go.Figure(go.Scatter(x=curve["Exit Date"], y=curve["Portfolio (₹)"], mode="lines+markers", line=dict(color="#00E5FF", width=3)))
                    fig.update_layout(title=f"{saved_symbol} Realised Capital Curve", template="plotly_dark", xaxis_title="Exit date", yaxis_title="Capital (₹)")
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(trade_df, use_container_width=True, hide_index=True)
                st.download_button("📥 Download Trade Log", make_excel_bytes({"Trades": trade_df, "Closed Trades": closed}), f"{saved_symbol}_Backtest_{saved_years}Y.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No qualifying trades were generated for this ticker and period.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        universe = c1.selectbox("Index Universe", list(UNIVERSE_MAP), index=3)
        years = c2.slider("Lookback Period (years)", 1, 10, 5)
        capital = c3.number_input("Starting Capital per Stock (₹)", min_value=1000, value=100000, step=10000)
        threshold = c4.slider("VAL Distance (%)", 0.5, 5.0, bt_val_default, 0.5, key="univ_val")
        atr_value, rr_value = st.columns(2)
        atr_mult_univ = atr_value.slider("ATR Stop Multiplier", 0.8, 2.5, bt_atr_default, 0.1, key="univ_atr")
        rr_univ = rr_value.slider("Minimum R:R", 0.8, 2.0, bt_rr_default, 0.1, key="univ_rr")
        st.caption("Universe results are independent per-stock trade sequences, not a single pooled portfolio. Capital is reset separately for each stock; do not add final values together as if all trades were executed concurrently.")
        if st.button(f"▶️ Run {universe} Universe Backtest", type="primary"):
            with st.spinner(f"Backtesting {len(UNIVERSE_MAP[universe])} symbols over {years} years. This can take several minutes..."):
                summary, all_trades = run_universe_backtest(universe, years, threshold, atr_mult_univ, rr_univ, capital)
            st.session_state["universe_backtest"] = (summary, all_trades, universe, years)
        saved_universe = st.session_state.get("universe_backtest")
        if saved_universe:
            summary, all_trades, saved_name, saved_years = saved_universe
            if not summary.empty:
                st.success(f"Backtest complete: qualifying trades found in {len(summary)} stocks.")
                if not all_trades.empty:
                    closed = all_trades[all_trades["Type"] != "Open at End ⚪"]
                    wins = int((closed["Type"] == "Target Hit 🟢").sum())
                    losses = int((closed["Type"] == "SL Hit 🔴").sum())
                    total = wins + losses
                    win_rate = wins / total * 100 if total else 0
                    n1, n2, n3, n4 = st.columns(4)
                    n1.metric("Completed Trades", f"{total:,}")
                    n2.metric("Wins / Losses", f"{wins:,} / {losses:,}")
                    n3.metric("Win Rate", f"{win_rate:.1f}%")
                    n4.metric("Stocks with Signals", f"{len(summary):,}")
                    st.markdown("### 📅 Universe-wide Yearly Breakdown")
                    if not closed.empty:
                        yearly = closed.groupby("Year", sort=True)
                        year_cols = st.columns(min(len(yearly), 5))
                        for idx, (year, group) in enumerate(yearly):
                            yw = int((group["Type"] == "Target Hit 🟢").sum())
                            yl = int((group["Type"] == "SL Hit 🔴").sum())
                            n = yw + yl
                            year_cols[idx % len(year_cols)].metric(str(year), f"{yw / n * 100:.1f}% win" if n else "—", f"{yw}W / {yl}L · {n} trades")
                st.subheader("📌 Stock Performance Summary")
                st.dataframe(summary, use_container_width=True, hide_index=True)
                st.subheader("📜 Complete Trade Execution Log")
                st.dataframe(all_trades, use_container_width=True, hide_index=True)
                failures = summary.attrs.get("failed_tickers", [])
                if failures:
                    st.caption(f"No usable Yahoo Finance data for {len(failures)} symbols. Some symbols may be delisted, renamed, or temporarily unavailable.")
                st.download_button("📥 Export Full Backtest Workbook", make_excel_bytes({"Stock Summary": summary, "All Trades": all_trades, "Closed Trades": all_trades[all_trades["Type"] != "Open at End ⚪"] if not all_trades.empty else pd.DataFrame()}), f"{saved_name.replace(' ', '_')}_{saved_years}Y_Backtest.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("No qualifying signals were found. Check the universe data status or try a wider VAL threshold / lower R:R.")

# ============================================================
# TAB 3 - NEWS
# ============================================================
with tab3:
    st.subheader("📰 Real-Time Global & Local Financial News")
    st.caption("Rule-based headline sentiment and keyword-based sector mapping. This is not an AI model or investment recommendation.")
    if st.button("🔄 Refresh Market News"):
        fetch_breaking_news.clear()
    news = fetch_breaking_news()
    if news:
        for item in news:
            safe_title = item["title"].replace("<", "&lt;").replace(">", "&gt;")
            safe_desc = item["description"].replace("<", "&lt;").replace(">", "&gt;")
            safe_impact = item["impact"].replace("<", "&lt;").replace(">", "&gt;")
            link_html = f'<a href="{item["link"]}" target="_blank" style="color:#00E5FF">Read source ↗</a>' if item["link"].startswith("http") else ""
            st.markdown(
                f'<div class="news-card"><span class="{item["badge"]}">{item["sentiment"]}</span>'
                f'<h4 style="margin:8px 0;color:#FFFFFF">{safe_title}</h4>'
                f'<p style="color:#94A3B8;font-size:.9rem">{safe_desc}</p>'
                f'<div style="margin-top:8px;font-size:.85rem;color:#00E5FF"><strong>🎯 Possible impact:</strong> {safe_impact}</div>{link_html}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Unable to fetch live news feeds at the moment. Please try refreshing later.")

# ============================================================
# SIDEBAR QUANT NOTES
# ============================================================
with st.sidebar:
    st.header("💬 AI Quant Assistant")
    st.caption("Quick strategy notes (rule-based; no external AI model is connected).")
    query = st.text_input("Enter a stock symbol or question:")
    if query:
        symbol_text = query.strip().upper()
        st.write(f"**Quant notes for `{symbol_text}`**")
        st.info(
            "1. Check the live scanner for price proximity to the prior 20-session volume-profile VAL.\n\n"
            "2. Confirm price is above EMA 200 and volume is at least 80% of its 20-session average.\n\n"
            "3. Review entry, stop, target and R:R; the scanner is a research filter, not a buy/sell instruction.\n\n"
            "4. Validate liquidity, corporate actions, results, broader trend and execution costs independently."
        )
    st.divider()
    st.caption("Backtest assumptions: daily OHLC data; signal at close; exit checks from next session; conservative stop-first rule when both levels trade in one candle; no brokerage, taxes, slippage or market impact included.")
