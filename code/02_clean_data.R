library(rvest)
library(tidyverse)
library(lubridate)

# ============================================
# 1. PARSE MINISTERS DATA
# ============================================
economia_page <- read_html("argentina-ministers-viz/data/economia.html")
economia_tables <- economia_page %>% html_elements("table.wikitable")
df_min_raw <- economia_tables[[1]] %>% html_table()

names(df_min_raw) <- c("ministerio", "numero", "ministro", "partido_na", "partido", "periodo", "duracion", "presidente")

df_min_raw <- df_min_raw %>%
  mutate(
    ministro = str_remove(ministro, "\\[.*?\\]$"),
    ministro = str_trim(ministro),
    presidente = str_remove(presidente, "\\[.*?\\]$"),
    presidente = str_trim(presidente),
    ministro = ifelse(ministro == "Ministro[2]", NA, ministro)
  ) %>%
  filter(!is.na(ministro))

parse_spanish_date <- function(date_str) {
  if(is.na(date_str) || date_str == "") return(NA_Date_)
  s <- str_to_lower(str_trim(date_str))
  s <- str_remove(s, "desde el ")
  s <- str_remove(s, "en el cargo")
  s <- str_trim(s)
  months_es <- c("enero"=1, "febrero"=2, "marzo"=3, "abril"=4, "mayo"=5, "junio"=6,
                 "julio"=7, "agosto"=8, "septiembre"=9, "octubre"=10, "noviembre"=11, "diciembre"=12)
  m <- str_match(s, "(\\d{1,2}) de ([a-zéóúíáñ]+) de (\\d{4})")
  if(!is.na(m[1,1])) {
    day <- as.integer(m[1,2])
    month_name <- m[1,3]
    year <- as.integer(m[1,4])
    month <- months_es[month_name]
    if(!is.na(month)) return(make_date(year, month, day))
  }
  return(NA_Date_)
}

df_min_raw <- df_min_raw %>%
  mutate(
    periodo_clean = str_remove(periodo, "\\[.*?\\]"),
    start_str = str_trim(str_extract(periodo_clean, "^[^—–\\-]+")),
    end_str = str_trim(str_extract(periodo_clean, "(?<=[—–\\-]).*$"))
  )

# Parse dates
df_min_raw$start_date <- as.Date(map_dbl(df_min_raw$start_str, function(x) {
  d <- parse_spanish_date(x); if(is.na(d)) return(NA_real_); as.numeric(d)
}), origin = "1970-01-01")

df_min_raw$end_date <- as.Date(map_dbl(df_min_raw$end_str, function(x) {
  d <- parse_spanish_date(x); if(is.na(d)) return(NA_real_); as.numeric(d)
}), origin = "1970-01-01")

# Debug dates
cat("Minister date class:", class(df_min_raw$start_date), "\n")
cat("Minister first dates:\n")
print(head(df_min_raw$start_date, 5))

df_min_raw <- df_min_raw %>%
  mutate(
    end_date = case_when(
      is.na(end_date) & str_detect(periodo, regex("desde|en el cargo", ignore_case = TRUE)) ~ today(),
      TRUE ~ end_date
    ),
    tenure_days = as.numeric(end_date - start_date),
    tenure_years = tenure_days / 365.25
  )

df_ministers <- df_min_raw %>%
  filter(year(start_date) >= 1880 | (is.na(start_date) & year(end_date) >= 1880)) %>%
  filter(!is.na(start_date)) %>%
  distinct(ministro, start_date, .keep_all = TRUE) %>%
  arrange(start_date)

cat("\nMinisters from 1880 onwards:", nrow(df_ministers), "\n")
cat("Date range:", as.character(min(df_ministers$start_date)), "to", as.character(max(df_ministers$end_date, na.rm=TRUE)), "\n")
cat("Average tenure (years):", round(mean(df_ministers$tenure_years, na.rm=TRUE), 2), "\n")

# ============================================
# 2. PARSE PRESIDENTS DATA
# ============================================
presidents_page <- read_html("argentina-ministers-viz/data/presidents.html")
pres_tables <- presidents_page %>% html_elements("table.wikitable")
df_pres_raw <- pres_tables[[12]] %>% html_table()

names(df_pres_raw) <- make.names(names(df_pres_raw), unique = TRUE)

# Remove header row
df_pres_raw <- df_pres_raw[-1, ]

# Rename
df_pres_raw <- df_pres_raw %>%
  rename(name_raw = Name.Birth.Death.,
         start = Term.of.office,
         end = Term.of.office.1,
         term_length = Term.of.office.2,
         party_en = Politicalparty.Coalition.,
         party_es = Politicalparty.Coalition..1,
         notes = Notes,
         vice_president = Vice.President)

# Clean names: remove birth/death years and term annotations
clean_president_name <- function(name) {
  if(is.na(name) || name == "") return(NA_character_)
  name <- str_remove(name, "\\(.*?\\)")
  name <- str_remove(name, "First term")
  name <- str_remove(name, "Second term")
  name <- str_remove(name, "First and Second terms")
  name <- str_remove(name, "Third term")
  name <- str_remove(name, "^\\(Presidency\\)")
  name <- str_trim(name)
  # Fix specific encoding issues
  name <- str_replace_all(name, "�", "")
  name <- str_trim(name)
  return(name)
}

df_pres_raw <- df_pres_raw %>%
  mutate(
    name = map_chr(name_raw, clean_president_name),
    start_date = dmy(start),
    end_date = case_when(
      str_to_lower(end) == "incumbent" ~ today(),
      TRUE ~ dmy(end)
    ),
    tenure_days = as.numeric(end_date - start_date),
    tenure_years = tenure_days / 365.25
  ) %>%
  filter(!is.na(name) & name != "")

# Filter to 1880 onwards
df_presidents <- df_pres_raw %>%
  filter(year(start_date) >= 1880 | (is.na(start_date) & year(end_date) >= 1880)) %>%
  filter(!is.na(start_date)) %>%
  arrange(start_date)

cat("\nPresidents from 1880 onwards:", nrow(df_presidents), "\n")
cat("President names:\n")
print(df_presidents$name)

# ============================================
# 3. CLASSIFY PRESIDENTS
# ============================================
df_presidents <- df_presidents %>%
  mutate(
    regime_type = case_when(
      name %in% c("José Félix Uriburu", "Pedro Pablo Ramírez", "Edelmiro Julián Farrell",
                  "Eduardo Lonardi", "Pedro Eugenio Aramburu",
                  "Juan Carlos Onganía", "Roberto Marcelo Levingston", "Alejandro Agustín Lanusse",
                  "Jorge Rafael Videla", "Roberto Eduardo Viola", "Leopoldo Galtieri", "Reynaldo Bignone",
                  "Junta of Commanders of the Armed Forces", "Military Junta") ~ "De facto",
      str_detect(notes, regex("coup|junta|de facto|provisional", ignore_case = TRUE)) ~ "De facto",
      TRUE ~ "De iure"
    ),
    regime_detail = case_when(
      name %in% c("José Félix Uriburu", "Pedro Pablo Ramírez", "Edelmiro Julián Farrell",
                  "Eduardo Lonardi", "Pedro Eugenio Aramburu",
                  "Juan Carlos Onganía", "Roberto Marcelo Levingston", "Alejandro Agustín Lanusse",
                  "Jorge Rafael Videla", "Roberto Eduardo Viola", "Leopoldo Galtieri", "Reynaldo Bignone",
                  "Junta of Commanders of the Armed Forces", "Military Junta") ~ "De facto (military)",
      name %in% c("Agustín Pedro Justo", "Roberto Marcelino Ortiz", "Ramón Castillo") ~ "De iure (fraudulent)",
      TRUE ~ "De iure (constitutional)"
    )
  )

cat("\nRegime type counts:\n")
print(table(df_presidents$regime_type))

# ============================================
# 4. LINK MINISTERS TO PRESIDENTS
# ============================================
find_president <- function(minister_start) {
  pres <- df_presidents %>%
    filter(start_date <= minister_start & end_date >= minister_start) %>%
    slice(1)
  if(nrow(pres) == 0) {
    pres <- df_presidents %>%
      mutate(dist = abs(as.numeric(start_date - minister_start))) %>%
      filter(dist == min(dist, na.rm = TRUE)) %>%
      slice(1)
  }
  return(pres)
}

df_ministers$president_name <- NA_character_
df_ministers$president_regime <- NA_character_
df_ministers$president_regime_detail <- NA_character_

for(i in seq_len(nrow(df_ministers))) {
  p <- find_president(df_ministers$start_date[i])
  if(nrow(p) > 0) {
    df_ministers$president_name[i] <- p$name[1]
    df_ministers$president_regime[i] <- p$regime_type[1]
    df_ministers$president_regime_detail[i] <- p$regime_detail[1]
  }
}

ministers_per_president <- df_ministers %>%
  group_by(president_name) %>%
  summarise(
    n_ministers = n(),
    avg_tenure_years = mean(tenure_years, na.rm=TRUE),
    .groups = "drop"
  ) %>%
  arrange(desc(n_ministers))

cat("\nTop presidents by number of economy ministers:\n")
print(head(ministers_per_president, 10))

# ============================================
# 5. SAVE
# ============================================
write_csv(df_ministers, "argentina-ministers-viz/data/ministers_clean.csv")
write_csv(df_presidents, "argentina-ministers-viz/data/presidents_clean.csv")
write_csv(ministers_per_president, "argentina-ministers-viz/data/ministers_per_president.csv")

cat("\nData saved.\n")
