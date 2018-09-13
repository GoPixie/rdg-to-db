CREATE VIEW nderivable_fare_ticket AS SELECT
ticket_code, origin_code, destination_code, route_code, railcard_code, rjfa_nfo.end_date as nderivable_end_date, rjfa_nfo.start_date as nderivable_start_date, rjfa_nfo.quote_date as nderivable_quote_date, suppress_mkr, adult_fare, child_fare, restriction_code, composite_indicator, cross_london_ind, ps_ind, rjfa_tty.end_date as ticket_end_date, rjfa_tty.start_date as ticket_start_date, rjfa_tty.quote_date as ticket_quote_date, description, tkt_class, tkt_type, tkt_group, last_valid_day, max_passengers, min_passengers, max_adults, min_adults, max_children, min_children, restricted_by_date, restricted_by_train, restricted_by_area, validity_code, atb_description, lul_xlondon_issue, reservation_required, capri_code, lul_93, uts_code, time_restriction, free_pass_lul, package_mkr, fare_multiplier, discount_category
FROM rjfa_nfo
INNER JOIN rjfa_tty
USING (ticket_code)
WHERE nd_record_type = 'O';

CREATE VIEW nderivable_fare_ticket_validity AS
SELECT  validity_code, ticket_code, origin_code, destination_code, route_code, railcard_code, nderivable_end_date, nderivable_start_date, nderivable_quote_date, suppress_mkr, adult_fare, child_fare, restriction_code, composite_indicator, cross_london_ind, ps_ind, ticket_end_date, ticket_start_date, ticket_quote_date, nderivable_fare_ticket.description, tkt_class, tkt_type, tkt_group, last_valid_day, max_passengers, min_passengers, max_adults, min_adults, max_children, min_children, restricted_by_date, restricted_by_train, restricted_by_area, atb_description, lul_xlondon_issue, reservation_required, capri_code, lul_93, uts_code, time_restriction, free_pass_lul, package_mkr, fare_multiplier, discount_category, rjfa_tvl.end_date as validity_end_date, rjfa_tvl.start_date as validity_start_date, rjfa_tvl.description as validity_description, out_days, out_months, ret_days, ret_months, ret_after_days, ret_after_months, ret_after_day, break_out, break_rtn, out_description, rtn_description
FROM nderivable_fare_ticket
INNER JOIN rjfa_tvl USING (validity_code);
