FORMS = ../modules/routing_procedures/forms/tsp.ui \
        ../modules/project_procedures/forms/ui_add_zoning.ui \
        ../modules/project_procedures/forms/ui_transponet_construction.ui \
        ../modules/paths_procedures/forms/advanced_graph_details.ui \
        ../modules/paths_procedures/forms/ui_compute_path.ui \
        ../modules/paths_procedures/forms/ui_impedance_matrix.ui \
        ../modules/paths_procedures/forms/ui_link_query_builder.ui \
        ../modules/paths_procedures/forms/ui_traffic_assignment.ui \
        ../modules/network/forms/ui_add_connectors.ui \
        ../modules/network/forms/ui_network_preparation.ui \
        ../modules/matrix_procedures/forms/ui_data_viewer.ui \
        ../modules/matrix_procedures/forms/ui_matrix_loader.ui \
        ../modules/matrix_procedures/forms/ui_matrix_viewer.ui \
        ../modules/matrix_procedures/forms/ui_project_data.ui \
        ../modules/matrix_procedures/forms/ui_vector_loader.ui \
        ../modules/gis/forms/ui_bandwidth_color_ramps.ui \
        ../modules/gis/forms/ui_bandwidths.ui \
        ../modules/gis/forms/ui_compare_scenarios.ui \
        ../modules/gis/forms/ui_DesireLines.ui \
        ../modules/gis/forms/ui_least_common_denominator.ui \
        ../modules/gis/forms/ui_simple_tag.ui \
        ../modules/forms/ui_MatrixViewer.ui \
        ../modules/forms/ui_nodes_to_areas.ui \
        ../modules/forms/ui_SegmentingLines.ui \
        ../modules/distribution_procedures/forms/ui_distribution.ui \
        ../modules/distribution_procedures/forms/ui_gravity_parameters.ui \
        ../modules/common_tools/forms/ui_about.ui \
        ../modules/common_tools/forms/ui_empty.ui \
        ../modules/common_tools/forms/ui_load_network_info.ui \
        ../modules/common_tools/forms/ui_parameters.ui \
        ../modules/common_tools/forms/ui_report.ui \

SOURCES = ../aequilibrae_menu.py \
          ../modules/routing_procedures/tsp_dialog.py \
          ../modules/project_procedures/creates_transponet_dialog.py \
          ../modules/project_procedures/project_from_osm_dialog.py \
          ../modules/paths_procedures/impedance_matrix_dialog.py \
        ../modules/paths_procedures/load_select_link_query_builder_dialog.py \
        ../modules/paths_procedures/show_shortest_path_dialog.py \
        ../modules/paths_procedures/traffic_assignment_dialog.py \
        ../modules/network/adds_connectors_dialog.py \
        ../modules/network/network_preparation_dialog.py \
        ../modules/matrix_procedures/display_aequilibrae_formats_dialog.py \
        ../modules/matrix_procedures/load_dataset_dialog.py \
        ../modules/matrix_procedures/load_matrix_dialog.py \
        ../modules/matrix_procedures/load_project_data.py \
        ../modules/matrix_procedures/matrix_manipulation_dialog.py \
        ../modules/gis/compare_scenarios_dialog.py \
        ../modules/gis/create_bandwidths_dialog.py \
        ../modules/gis/desire_lines_dialog.py \
        ../modules/gis/simple_tag_dialog.py \
        ../modules/distribution_procedures/distribution_models_dialog.py \
        ../modules/common_tools/about_dialog.py \
        ../modules/common_tools/load_graph_layer_setting_dialog.py \
        ../modules/common_tools/log_dialog.py \
        ../modules/common_tools/parameters_dialog.py \
        ../modules/common_tools/report_dialog.py

TRANSLATIONS = aequilibrae_pt_BR.ts