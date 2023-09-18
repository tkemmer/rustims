use rust_tdf::data::handle::TimsDataset;

fn main() {
    let data_path = "/media/hd01/CCSPred/M210115_001_Slot1-1_1_850.d";
    let bruker_lib_path = "/home/administrator/Documents/promotion/rust/rust_tdf/libs/libtimsdata.so";
    let tims_data = TimsDataset::new(bruker_lib_path, data_path);
    match tims_data {
        Ok(tims_data) => {
            for i in 1..66074 {
                let frame = tims_data.get_frame(i);
                match frame {
                    Ok(frame) => println!("frame id: {:?}, first 5 mz values: {:?}", i, frame.2[..1].to_vec()),
                    Err(e) => println!("error: {}", e),
                };
            }
        },
        Err(e) => println!("error: {}", e),
    };
}