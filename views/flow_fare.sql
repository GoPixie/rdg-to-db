
CREATE VIEW rjfa_ffl_f_dual AS
    SELECT origin_code, destination_code, route_code, status_code, usage_code, end_date, start_date, toc, cross_london_ind, ns_disc_ind, publication_ind, flow_id
    FROM rjfa_ffl_f
UNION
    SELECT destination_code as origin_code, origin_code as destination_code, route_code, status_code, usage_code, end_date, start_date, toc, cross_london_ind, ns_disc_ind, publication_ind, flow_id
    FROM rjfa_ffl_f
    WHERE direction = 'R';


-- -- this is useless; lookup based on uic_code across the join is too slow
-- CREATE MATERIALIZED VIEW rjfa_loc_l_nlc_uic_mapping AS
-- SELECT DISTINCT uic_code, nlc_code
-- FROM rjfa_loc_l;
-- -- join for flow_fare would have been:
-- INNER JOIN rjfa_loc_l_nlc_uic_mapping origin_loc on (rjfa_ffl_f_dual.origin_code = origin_loc.nlc_code)
-- INNER JOIN rjfa_loc_l_nlc_uic_mapping destination_loc on (rjfa_ffl_f_dual.destination_code = destination_loc.nlc_code)
-- -- additional select for flow_fare would have been:
-- origin_loc.uic_code as origin_uic, destination_loc.uic_code as destination_uic,


CREATE VIEW flow_fare AS
SELECT origin_code, destination_code, ticket_code, fare, restriction_code, route_code, status_code, usage_code, rjfa_ffl_f_dual.end_date, rjfa_ffl_f_dual.start_date, toc, cross_london_ind, ns_disc_ind, publication_ind from rjfa_ffl_f_dual
INNER JOIN rjfa_ffl_t using (flow_id)
WHERE usage_code != 'C'; -- C type records are summation records, used for creating G records and are not used for chargeable fares.  These have been removed with introduction of PMS;


CREATE VIEW flow_fare_ticket AS
SELECT flow_fare.origin_code,
    flow_fare.destination_code,
    ticket_code,
    flow_fare.fare,
    flow_fare.restriction_code,
    flow_fare.route_code,
    flow_fare.status_code,
    flow_fare.usage_code,
    flow_fare.end_date as flow_end_date,
    flow_fare.start_date as flow_start_date,
    flow_fare.toc,
    flow_fare.cross_london_ind,
    flow_fare.ns_disc_ind,
    flow_fare.publication_ind,
    rjfa_tty.end_date as ticket_end_date,
    rjfa_tty.start_date as ticket_start_date,
    rjfa_tty.quote_date as ticket_quote_date,
    rjfa_tty.description as ticket_description,
    rjfa_tty.tkt_class,
    rjfa_tty.tkt_type,
    rjfa_tty.tkt_group,
    rjfa_tty.last_valid_day,
    rjfa_tty.max_passengers,
    rjfa_tty.min_passengers,
    rjfa_tty.max_adults,
    rjfa_tty.min_adults,
    rjfa_tty.max_children,
    rjfa_tty.min_children,
    rjfa_tty.restricted_by_date,
    rjfa_tty.restricted_by_train,
    rjfa_tty.restricted_by_area,
    rjfa_tty.validity_code,
    rjfa_tty.atb_description,
    rjfa_tty.lul_xlondon_issue,
    rjfa_tty.reservation_required,
    rjfa_tty.capri_code,
    rjfa_tty.lul_93,
    rjfa_tty.uts_code,
    rjfa_tty.time_restriction,
    rjfa_tty.free_pass_lul,
    rjfa_tty.package_mkr,
    rjfa_tty.fare_multiplier,
    rjfa_tty.discount_category
FROM flow_fare INNER JOIN rjfa_tty using (ticket_code);



CREATE VIEW flow_fare_ticket_validity AS
SELECT flow_fare_ticket.origin_code,
    flow_fare_ticket.destination_code,
    flow_fare_ticket.ticket_code,
    flow_fare_ticket.fare,
    flow_fare_ticket.restriction_code,
    flow_fare_ticket.route_code,
    flow_fare_ticket.status_code,
    flow_fare_ticket.usage_code,
    flow_fare_ticket.flow_end_date,
    flow_fare_ticket.flow_start_date,
    flow_fare_ticket.toc,
    flow_fare_ticket.cross_london_ind,
    flow_fare_ticket.ns_disc_ind,
    flow_fare_ticket.publication_ind,
    flow_fare_ticket.ticket_end_date,
    flow_fare_ticket.ticket_start_date,
    flow_fare_ticket.ticket_quote_date,
    flow_fare_ticket.ticket_description,
    flow_fare_ticket.tkt_class,
    flow_fare_ticket.tkt_type,
    flow_fare_ticket.tkt_group,
    flow_fare_ticket.last_valid_day,
    flow_fare_ticket.max_passengers,
    flow_fare_ticket.min_passengers,
    flow_fare_ticket.max_adults,
    flow_fare_ticket.min_adults,
    flow_fare_ticket.max_children,
    flow_fare_ticket.min_children,
    flow_fare_ticket.restricted_by_date,
    flow_fare_ticket.restricted_by_train,
    flow_fare_ticket.restricted_by_area,
    validity_code,
    flow_fare_ticket.atb_description,
    flow_fare_ticket.lul_xlondon_issue,
    flow_fare_ticket.reservation_required,
    flow_fare_ticket.capri_code,
    flow_fare_ticket.lul_93,
    flow_fare_ticket.uts_code,
    flow_fare_ticket.time_restriction,
    flow_fare_ticket.free_pass_lul,
    flow_fare_ticket.package_mkr,
    flow_fare_ticket.fare_multiplier,
    flow_fare_ticket.discount_category,
    rjfa_tvl.end_date as validity_end_date,
    rjfa_tvl.start_date as validity_start_date,
    rjfa_tvl.description as validity_description,
    rjfa_tvl.out_days,
    rjfa_tvl.out_months,
    rjfa_tvl.ret_days,
    rjfa_tvl.ret_months,
    rjfa_tvl.ret_after_days,
    rjfa_tvl.ret_after_months,
    rjfa_tvl.ret_after_day,
    rjfa_tvl.break_out,
    rjfa_tvl.break_rtn,
    rjfa_tvl.out_description,
    rjfa_tvl.rtn_description
FROM flow_fare_ticket INNER JOIN rjfa_tvl using (validity_code);


CREATE VIEW restriction_header AS SELECT
rjfa_rst_rh.cf_mkr,
    rjfa_rst_rh.restriction_code,
    rjfa_rst_rh.description,
    rjfa_rst_rh.desc_out,
    rjfa_rst_rh.desc_rtn,
    rjfa_rst_rh.type_out,
    rjfa_rst_rh.type_rtn,
    rjfa_rst_rh.change_ind,
    rjfa_rst_hd.date_from,
    rjfa_rst_hd.date_to,
    rjfa_rst_hd.days,
    rjfa_rst_hl.location_crs_code,
    rjfa_rst_hc.allowed_change,
    rjfa_rst_ha.additional_restriction,
    rjfa_rst_ha.origin,
    rjfa_rst_ha.destination
   FROM rjfa_rst_rh
     LEFT JOIN rjfa_rst_hd USING (cf_mkr, restriction_code)
     LEFT JOIN rjfa_rst_hl USING (cf_mkr, restriction_code)
     LEFT JOIN rjfa_rst_hc USING (cf_mkr, restriction_code)
     LEFT JOIN rjfa_rst_ha USING (cf_mkr, restriction_code);


CREATE VIEW time_restriction AS
 SELECT rjfa_rst_tr.cf_mkr,
    rjfa_rst_tr.restriction_code,
    rjfa_rst_tr.sequence_no,
    rjfa_rst_tr.out_ret AS tr_out_ret,
    rjfa_rst_tr.time_from,
    rjfa_rst_tr.time_to,
    rjfa_rst_tr.arr_dep_via,
    rjfa_rst_tr.location,
    rjfa_rst_tr.rstr_type,
    rjfa_rst_tr.train_type,
    rjfa_rst_tr.min_fare_flag,
    rjfa_rst_td.out_ret AS td_out_ret,
    rjfa_rst_td.date_from,
    rjfa_rst_td.date_to,
    rjfa_rst_td.days,
    rjfa_rst_tt.out_ret AS tt_out_ret,
    rjfa_rst_tt.toc_code
   FROM rjfa_rst_tr
     LEFT JOIN rjfa_rst_td USING (cf_mkr, restriction_code, sequence_no)
     LEFT JOIN rjfa_rst_tt USING (cf_mkr, restriction_code, sequence_no);

CREATE VIEW train_restriction AS
 SELECT rjfa_rst_sr.cf_mkr,
    rjfa_rst_sr.restriction_code,
    rjfa_rst_sr.train_no,
    rjfa_rst_sr.out_ret,
    rjfa_rst_sr.sleeper_ind,
    rjfa_rst_sd.date_from,
    rjfa_rst_sd.date_to,
    rjfa_rst_sd.days,
    rjfa_rst_sq.location,
    rjfa_rst_sq.arr_dep
   FROM rjfa_rst_sr
     LEFT JOIN rjfa_rst_sd USING (cf_mkr, restriction_code, train_no, out_ret)
     LEFT JOIN rjfa_rst_sq USING (cf_mkr, restriction_code, train_no, out_ret);


CREATE VIEW status_discount AS
  SELECT *
  FROM rjfa_dis_s
  INNER JOIN rjfa_dis_d USING (status_code, end_date);
