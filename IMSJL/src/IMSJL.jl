module IMSJL

export TimsDataHandle_new, TimsDataHandle_get_data_path, TimsDataHandle_destroy, TimsDataHandle_get_frame_count, TimsDataHandle_get_frame

struct CTimsFrame
    frame_id::Int32
    ms_type_numeric::Int32
    retention_time::Float64
    scan::Ptr{Int32}
    inv_mobility::Ptr{Float64}
    tof::Ptr{Int32}
    mz::Ptr{Float64}
    intensity::Ptr{Float64}
end

struct TimsFrame
    frame_id::Int32
    ms_type_numeric::Int32
    retention_time::Float64
    scan::Vector{Int32}
    inv_mobility::Vector{Float64}
    tof::Vector{Int32}
    mz::Vector{Float64}
    intensity::Vector{Float64}
end

const lib = "/home/administrator/Documents/promotion/rustims/imsjl_connector/target/release/libimsjl_connector.so"

function TimsDataHandle_new(data_path::String, bruker_lib_path::String)
    ccall((:tims_data_handle_new, lib), Ptr{Cvoid}, (Cstring, Cstring), data_path, bruker_lib_path)
end

function TimsDataHandle_get_data_path(handle::Ptr{Cvoid})::String
    return unsafe_string(ccall((:tims_data_handle_get_data_path, lib), Cstring, (Ptr{Cvoid},), handle))
end

function TimsDataHandle_get_bruker_binary_path(handle::Ptr{Cvoid})::String
    return unsafe_string(ccall((:tims_data_handle_get_bruker_binary_path, lib), Cstring, (Ptr{Cvoid},), handle))
end

function TimsDataHandle_get_frame_count(handle::Ptr{Cvoid})::Int32
    return ccall((:tims_data_handle_get_frame_count, lib), Int32, (Ptr{Cvoid},), handle)
end

function TimsDataHandle_destroy(handle::Ptr{Cvoid})
    ccall((:tims_data_handle_destroy, lib), Cvoid, (Ptr{Cvoid},), handle)
end

function TimsDataHandle_get_frame(handle::Ptr{Cvoid}, frame_id::Int32)::CTimsFrame
    ccall((:tims_data_handle_get_frame, lib), CTimsFrame, (Ptr{Cvoid}, Int32), handle, frame_id)
end

function convert_ctims_frame_to_julia(ctims_frame::CTimsFrame)::TimsFrame

    # Assuming you also have lengths for each array in CTimsFrame or a predefined length
    julia_scan = unsafe_wrap(Array, ctims_frame.scan, length_of_scan, own=true)
    julia_inv_mobility = unsafe_wrap(Array, ctims_frame.inv_mobility, length_of_inv_mobility, own=true)
    julia_tof = unsafe_wrap(Array, ctims_frame.tof, length_of_tof, own=true)
    julia_mz = unsafe_wrap(Array, ctims_frame.mz, length_of_mz, own=true)
    julia_intensity = unsafe_wrap(Array, ctims_frame.intensity, length_of_intensity, own=true)

    TimsFrame(
        ctims_frame.frame_id,
        ctims_frame.ms_type_numeric,
        ctims_frame.retention_time,
        julia_scan,
        julia_inv_mobility,
        julia_tof,
        julia_mz,
        julia_intensity
    )
end


end # module IMSJL
