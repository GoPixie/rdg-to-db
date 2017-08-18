
CREATE VIEW rjfa_rte_l_agg AS
SELECT route_code, end_date,
array_remove(array_agg(CASE WHEN incl_excl = 'I' THEN rjfa_rte_l.crs_code
    ELSE null END), null) AS crs_inclusions,
array_remove(array_agg(CASE WHEN incl_excl = 'E' THEN rjfa_rte_l.crs_code
    ELSE null END), null) AS crs_exclusions,
array_remove(array_agg(CASE WHEN incl_excl = 'I' THEN rjfa_rte_l.nlc_code
    ELSE null END), null) AS nls_inclusions,
array_remove(array_agg(CASE WHEN incl_excl = 'E' THEN rjfa_rte_l.nlc_code
    ELSE null END), null) AS nlc_exclusions
FROM rjfa_rte_l
GROUP BY route_code, end_date;

CREATE VIEW rjrg_rgk_d_agg AS
SELECT route_code,
array_remove(array_agg(CASE WHEN entry_type = 'A' THEN rjrg_rgk_d.crs_code
    ELSE null END), null) AS rgk_crs_inclusions,
array_remove(array_agg(CASE WHEN entry_type = 'I' THEN rjrg_rgk_d.crs_code
    ELSE null END), null) AS rgk_crs_anys,
array_remove(array_agg(CASE WHEN entry_type = 'E' THEN rjrg_rgk_d.crs_code
    ELSE null END), null) AS rgk_crs_exclusions,
array_remove(array_agg(CASE WHEN entry_type = 'T' THEN rjrg_rgk_d.toc_id
    ELSE null END), null) AS toc_inclusions,
array_remove(array_agg(CASE WHEN entry_type = 'X' THEN rjrg_rgk_d.toc_id
    ELSE null END), null) AS toc_exclusions,
array_remove(array_agg(CASE WHEN entry_type = 'L' THEN rjrg_rgk_d.mode_code
    ELSE null END), null) AS mode_inclusions,
array_remove(array_agg(CASE WHEN entry_type = 'N' THEN rjrg_rgk_d.mode_code
    ELSE null END), null) AS mode_exclusions
FROM rjrg_rgk_d
GROUP BY route_code;

CREATE VIEW route_code AS
SELECT route_code, daterange(start_date, CASE WHEN end_date = '2999-12-31' THEN null
    ELSE end_date+1 END) AS date_range, quote_date, description,
concat(atb_desc_1, atb_desc_2, atb_desc_3, atb_desc_4) AS atb_desc,
crs_inclusions, crs_exclusions, rgk_crs_inclusions, rgk_crs_anys,
rgk_crs_exclusions, rjrg_rgk_l.london_marker,
toc_inclusions, toc_exclusions, mode_inclusions, mode_exclusions
FROM rjfa_rte_r
LEFT JOIN rjfa_rte_l_agg USING (route_code, end_date)
LEFT JOIN rjrg_rgk_l USING (route_code)
LEFT JOIN rjrg_rgk_d_agg USING (route_code);
