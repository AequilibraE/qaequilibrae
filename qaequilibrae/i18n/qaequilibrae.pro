FORMS = ../modules/distribution_procedures/forms/ui_distribution.ui \
 ../modules/distribution_procedures/forms/ui_gravity_parameters.ui \
 ../modules/paths_procedures/forms/advanced_graph_details.ui \
 ../modules/paths_procedures/forms/ui_traffic_assignment.ui \
 ../modules/paths_procedures/forms/ui_compute_path.ui \
 ../modules/paths_procedures/forms/ui_link_query_builder.ui \
 ../modules/paths_procedures/forms/ui_impedance_matrix.ui \
 ../modules/matrix_procedures/forms/ui_matrix_viewer.ui \
 ../modules/matrix_procedures/forms/ui_project_data.ui \
 ../modules/matrix_procedures/forms/ui_vector_loader.ui \
 ../modules/matrix_procedures/forms/ui_data_viewer.ui \
 ../modules/matrix_procedures/forms/ui_matrix_loader.ui \
 ../modules/forms/ui_nodes_to_areas.ui \
 ../modules/forms/ui_MatrixViewer.ui \
 ../modules/forms/ui_SegmentingLines.ui \
 ../modules/project_procedures/forms/ui_add_zoning.ui \
 ../modules/project_procedures/forms/ui_transponet_construction.ui \
 ../modules/routing_procedures/forms/tsp.ui \
 ../modules/network/forms/ui_network_preparation.ui \
 ../modules/network/forms/ui_add_connectors.ui \
 ../modules/gis/forms/ui_bandwidth_color_ramps.ui \
 ../modules/gis/forms/ui_simple_tag.ui \
 ../modules/gis/forms/ui_compare_scenarios.ui \
 ../modules/gis/forms/ui_bandwidths.ui \
 ../modules/gis/forms/ui_DesireLines.ui \
 ../modules/gis/forms/ui_least_common_denominator.ui \
 ../modules/public_transport_procedures/forms/ui_gtfs_viewer.ui \
 ../modules/common_tools/forms/ui_report.ui \
 ../modules/common_tools/forms/ui_empty.ui \
 ../modules/common_tools/forms/ui_about.ui \
 ../modules/common_tools/forms/ui_parameters.ui \
 ../modules/common_tools/forms/ui_load_network_info.ui

SOURCES = ../qaequilibrae.py \
 ../modules/distribution_procedures/distribution_models_dialog.py \
 ../modules/paths_procedures/impedance_matrix_dialog.py \
 ../modules/paths_procedures/traffic_assignment_dialog.py \
 ../modules/paths_procedures/show_shortest_path_dialog.py \
 ../modules/matrix_procedures/load_dataset_dialog.py \
 ../modules/matrix_procedures/matrix_manipulation_dialog.py \
 ../modules/matrix_procedures/load_project_data.py \
 ../modules/matrix_procedures/load_matrix_dialog.py \
 ../modules/matrix_procedures/load_dataset_class.py \
 ../modules/matrix_procedures/mat_reblock.py \
 ../modules/matrix_procedures/display_aequilibrae_formats_dialog.py \
 ../modules/matrix_procedures/results_lister.py \
 ../modules/matrix_procedures/matrix_lister.py \
 ../modules/matrix_procedures/load_matrix_class.py \
 ../modules/project_procedures/creates_transponet_dialog.py \
 ../modules/project_procedures/add_zones_procedure.py \
 ../modules/project_procedures/creates_transponet_procedure.py \
 ../modules/project_procedures/project_from_osm_dialog.py \
 ../modules/routing_procedures/tsp_dialog.py \
 ../modules/network/network_preparation_dialog.py \
 ../modules/network/Network_preparation_procedure.py \
 ../modules/menu_actions/action_show_project_data.py \
 ../modules/menu_actions/action_gis_scenario_comparison.py \
 ../modules/menu_actions/action_show_log.py \
 ../modules/menu_actions/load_project_action.py \
 ../modules/menu_actions/action_add_zoning.py \
 ../modules/menu_actions/action_add_connectors.py \
 ../modules/gis/compare_scenarios_dialog.py \
 ../modules/gis/least_common_denominator_dialog.py \
 ../modules/gis/least_common_denominator_procedure.py \
 ../modules/gis/simple_tag_dialog.py \
 ../modules/gis/simple_tag_procedure.py \
 ../modules/gis/desire_lines_dialog.py \
 ../modules/gis/desire_lines_procedure.py \
 ../modules/common_tools/report_dialog.py \
 ../modules/common_tools/get_output_file_name.py \
 ../modules/common_tools/parameters_dialog.py

TRANSLATIONS = qaequilibrae.ts