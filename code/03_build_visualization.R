library(tidyverse)
library(plotly)
library(lubridate)

# ============================================
# LOAD & CLEAN DATA
# ============================================
df_ministers <- read_csv("argentina-ministers-viz/data/ministers_clean.csv", show_col_types = FALSE)
df_presidents <- read_csv("argentina-ministers-viz/data/presidents_clean.csv", show_col_types = FALSE)

# Encoding fix
df_presidents$name <- iconv(df_presidents$name_raw, from = "UTF-8", to = "UTF-8", sub = "")
df_ministers$ministro <- iconv(df_ministers$ministro, from = "UTF-8", to = "UTF-8", sub = "")
df_ministers$president_name <- iconv(df_ministers$president_name, from = "UTF-8", to = "UTF-8", sub = "")

# Re-classify
df_presidents <- df_presidents %>%
  mutate(
    regime_type = case_when(
      str_detect(name, regex("Uriburu,José Félix|Ramírez,Pedro Pablo|Farrell,Edelmiro|Lonardi|Eduardo|Aramburu,Pedro Eugenio|Onganía|Levingston|Lanusse|Videla|Viola|Galtieri|Bignone|Junta", ignore_case = TRUE)) ~ "De facto",
      str_detect(notes, regex("coup|junta|de facto|provisional", ignore_case = TRUE)) ~ "De facto",
      TRUE ~ "De iure"
    ),
    regime_detail = case_when(
      str_detect(name, regex("Uriburu,José Félix|Ramírez,Pedro Pablo|Farrell,Edelmiro|Lonardi|Eduardo|Aramburu,Pedro Eugenio|Onganía|Levingston|Lanusse|Videla|Viola|Galtieri|Bignone|Junta", ignore_case = TRUE)) ~ "De facto (military)",
      str_detect(name, regex("Justo,Agustín|Ortiz,Roberto|Castillo,Ramón", ignore_case = TRUE)) ~ "De iure (fraudulent)",
      TRUE ~ "De iure (constitutional)"
    ),
    regime_color = case_when(
      regime_detail == "De facto (military)" ~ "#dc2626",
      regime_detail == "De iure (fraudulent)" ~ "#f59e0b",
      TRUE ~ "#2563eb"
    )
  )

# Re-link ministers
find_president <- function(minister_start) {
  pres <- df_presidents %>% filter(start_date <= minister_start & end_date >= minister_start) %>% slice(1)
  if(nrow(pres) == 0) {
    pres <- df_presidents %>% mutate(dist = abs(as.numeric(start_date - minister_start))) %>%
      filter(dist == min(dist, na.rm = TRUE)) %>% slice(1)
  }
  return(pres)
}

for(i in seq_len(nrow(df_ministers))) {
  p <- find_president(df_ministers$start_date[i])
  if(nrow(p) > 0) {
    df_ministers$president_name[i] <- p$name[1]
    df_ministers$president_regime[i] <- p$regime_type[1]
    df_ministers$president_regime_detail[i] <- p$regime_detail[1]
    df_ministers$president_color[i] <- p$regime_color[1]
  }
}

# ============================================
# STATS
# ============================================
total_ministers <- nrow(df_ministers)
avg_tenure <- mean(df_ministers$tenure_years, na.rm = TRUE)
med_tenure <- median(df_ministers$tenure_years, na.rm = TRUE)

ministers_per_president <- df_ministers %>%
  group_by(president_name, president_regime_detail) %>%
  summarise(n = n(), avg_ten = mean(tenure_years, na.rm = TRUE), .groups = "drop") %>%
  arrange(n)

n_pres <- nrow(df_presidents)
n_defacto <- sum(df_presidents$regime_type == "De facto")

# ============================================
# PLOT 1: COMPACT DENSITY TIMELINE
# ============================================
# Presidents as background bars at y=1, ministers as vertical ticks at y=0.5-0.9

p1 <- plot_ly(height = 650)

# Background president bars (thick, at top)
for(i in seq_len(nrow(df_presidents))) {
  pr <- df_presidents[i, ]
  p1 <- add_segments(
    p1, x = pr$start_date, xend = pr$end_date,
    y = 1, yend = 1,
    line = list(color = pr$regime_color, width = 55),
    hoverinfo = "text",
    text = paste0("<b>", pr$name, "</b><br>", pr$regime_detail, "<br>",
                  format(pr$start_date, "%b %Y"), " – ", format(pr$end_date, "%b %Y"), "<br>",
                  round(pr$tenure_years, 1), " years"),
    showlegend = FALSE
  )
}

# Ministers as vertical ticks
for(i in seq_len(nrow(df_ministers))) {
  m <- df_ministers[i, ]
  p1 <- add_segments(
    p1, x = m$start_date, xend = m$start_date,
    y = 0.45, yend = 0.78,
    line = list(color = "#16a34a", width = 2.5),
    hoverinfo = "text",
    text = paste0("<b>", m$ministro, "</b><br>Under: ", m$president_name, "<br>",
                  format(m$start_date, "%b %Y"), " – ", format(m$end_date, "%b %Y"), "<br>",
                  round(m$tenure_years, 2), " yr"),
    showlegend = FALSE,
    opacity = 0.7
  )
}

# Crisis lines
crises <- tibble(
  date = as.Date(c("1890-04-01", "1930-09-06", "1955-09-16", "1966-06-28", 
                    "1976-03-24", "1989-07-08", "2001-12-20", "2023-12-10")),
  label = c("1890 Crisis", "1930 Coup", "1955 Coup", "1966 Coup", 
            "1976 Coup", "1989 Hyperinfl.", "2001 Default", "Milei")
)

for(i in seq_len(nrow(crises))) {
  p1 <- add_segments(
    p1, x = crises$date[i], xend = crises$date[i],
    y = 0.35, yend = 1.18,
    line = list(color = "rgba(80,80,80,0.4)", width = 1, dash = "dot"),
    showlegend = FALSE, hoverinfo = "skip"
  )
}

# Crisis labels above
p1 <- add_text(
  p1, data = crises, x = ~date, y = 1.22,
  text = ~label, textposition = "top center",
  textfont = list(size = 11, color = "#374151"),
  showlegend = FALSE, hoverinfo = "skip"
)

p1 <- layout(
  p1,
  xaxis = list(
    title = list(text = "Year", font = list(size = 14)),
    type = "date", tickformat = "%Y", dtick = "M120",
    showgrid = TRUE, gridcolor = "#e5e7eb",
    zeroline = FALSE, tickfont = list(size = 12)
  ),
  yaxis = list(
    visible = FALSE,
    range = c(0.2, 1.4)
  ),
  plot_bgcolor = "#f9fafb",
  paper_bgcolor = "#ffffff",
  margin = list(l = 60, r = 40, t = 20, b = 60),
  hovermode = "closest"
)

# ============================================
# PLOT 2: BAR CHART — MINISTERS PER PRESIDENT
# ============================================
df_bar <- ministers_per_president %>%
  mutate(color = case_when(
    president_regime_detail == "De facto (military)" ~ "#dc2626",
    president_regime_detail == "De iure (fraudulent)" ~ "#f59e0b",
    TRUE ~ "#2563eb"
  ))

p2 <- plot_ly(
  data = df_bar, y = ~reorder(president_name, n), x = ~n,
  type = "bar", marker = list(color = ~color),
  text = ~paste0(n, " ministers"), hoverinfo = "text",
  showlegend = FALSE
) %>% layout(
  title = list(text = "<b>Ministers per President</b>", font = list(size = 16)),
  xaxis = list(title = "Count", tickfont = list(size = 11)),
  yaxis = list(tickfont = list(size = 10)),
  plot_bgcolor = "#f9fafb", paper_bgcolor = "#ffffff",
  margin = list(l = 140, r = 30, t = 50, b = 40)
)

# ============================================
# PLOT 3: TENURE HISTOGRAM
# ============================================
p3 <- plot_ly(
  data = df_ministers, x = ~tenure_years, type = "histogram", nbinsx = 25,
  marker = list(color = "#16a34a", line = list(color = "#15803d", width = 1)),
  hovertemplate = "%{x:.1f} yr: %{y} ministers<extra></extra>"
) %>% layout(
  title = list(text = "<b>How Long Do They Last?</b>", font = list(size = 16)),
  xaxis = list(title = "Years in office", tickfont = list(size = 11)),
  yaxis = list(title = "Ministers", tickfont = list(size = 11)),
  plot_bgcolor = "#f9fafb", paper_bgcolor = "#ffffff",
  margin = list(l = 50, r = 30, t = 50, b = 40),
  shapes = list(
    list(type = "line", x0 = med_tenure, x1 = med_tenure, y0 = 0, y1 = 1, yref = "paper",
         line = list(color = "#dc2626", width = 2, dash = "dash"))
  ),
  annotations = list(
    list(x = med_tenure, y = 1, yref = "paper", text = paste("Median:", round(med_tenure, 1), "yr"),
         showarrow = FALSE, yshift = 14, font = list(color = "#dc2626", size = 12))
  )
)

# ============================================
# PLOT 4: BIG STATS (text-based)
# ============================================
stats_text <- paste0(
  "<b style='font-size:42px;color:#1f2937;'>", total_ministers, "</b>",
  "<span style='font-size:14px;color:#6b7280;'> ministers since 1880</span><br><br>",
  "<b style='font-size:42px;color:#1f2937;'>", round(avg_tenure, 1), "</b>",
  "<span style='font-size:14px;color:#6b7280;'> yr average tenure</span><br><br>",
  "<b style='font-size:42px;color:#dc2626;'>", n_defacto, "</b>",
  "<span style='font-size:14px;color:#6b7280;'> de facto presidents</span><br><br>",
  "<b style='font-size:42px;color:#2563eb;'>", n_pres, "</b>",
  "<span style='font-size:14px;color:#6b7280;'> total presidents</span>"
)

p4 <- plot_ly(height = 400) %>%
  add_text(x = 0.5, y = 0.5, text = stats_text,
           textposition = "middle center",
           textfont = list(family = "Arial, sans-serif"),
           showlegend = FALSE, hoverinfo = "skip") %>%
  layout(
    xaxis = list(visible = FALSE, range = c(0, 1)),
    yaxis = list(visible = FALSE, range = c(0, 1)),
    paper_bgcolor = "#ffffff",
    margin = list(l = 20, r = 20, t = 20, b = 20)
  )

# ============================================
# ASSEMBLE DASHBOARD-LAYOUT
# ============================================
# Top: full-width timeline
# Bottom-left: bar chart | Bottom-center: histogram | Bottom-right: big stats

bottom_row <- subplot(p2, p3, p4, nrows = 1, widths = c(0.40, 0.35, 0.25), margin = 0.04)

fig <- subplot(p1, bottom_row, nrows = 2, heights = c(0.55, 0.45), margin = 0.06) %>%
  layout(
    title = list(
      text = paste0(
        "<b>Argentina's Political & Economic Instability (1880–Present)</b><br>",
        "<sup>Sources: Wikipedia (Ministers of Economy; Presidents of Argentina)</sup>"
      ),
      font = list(size = 22, family = "Arial, sans-serif"),
      x = 0.5
    ),
    margin = list(l = 40, r = 30, t = 110, b = 30),
    paper_bgcolor = "#ffffff",
    annotations = list(
      list(
        x = 0.01, y = 0.99, xref = "paper", yref = "paper",
        text = paste0(
          "<b>Legend</b><br>",
          "<span style='color:#2563eb'>■</span> De iure president<br>",
          "<span style='color:#f59e0b'>■</span> Fraudulent elections<br>",
          "<span style='color:#dc2626'>■</span> De facto / coup<br>",
          "<span style='color:#16a34a'>▕</span> Minister appointed<br>",
          "<span style='color:#6b7280'>┇</span> Crisis"
        ),
        showarrow = FALSE, align = "left",
        bgcolor = "rgba(255,255,255,0.95)",
        bordercolor = "#DDD", borderwidth = 1,
        font = list(size = 12)
      )
    )
  )

# Save
htmlwidgets::saveWidget(
  fig,
  "argentina-ministers-viz/output/argentina_ministers_timeline.html",
  selfcontained = TRUE,
  title = "Argentina's Economy Ministers & Presidents (1880–Present)"
)

file.copy(
  "argentina-ministers-viz/output/argentina_ministers_timeline.html",
  "argentina-ministers-viz/output/index.html",
  overwrite = TRUE
)

cat("Done. Output saved to argentina-ministers-viz/output/\n")
