module Data

import Base.show

@enum MsType PRECURSOR=0 FRAGMENT_DDA=8 FRAGMENT_DIA=9 UNKNOWN=-1

struct TimsFrame
    frame_id::Int32
    ms_type::MsType
    retention_time::Float64
    scan::Vector{Int32}
    inv_mobility::Vector{Float64}
    tof::Vector{Int32}
    mz::Vector{Float64}
    intensity::Vector{Float64}
end

function show(io::IO, frame::TimsFrame)
    num_peaks = length(frame.mz)
    print(io, "TimsFrame(frame_id=$(frame.frame_id), ms_type=$(frame.ms_type_numeric), num_peaks=$num_peaks)")
end

export TimsFrame

end