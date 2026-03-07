// build.rs — Rust proto code generation using prost-build
//
// Place this file at the root of your Rust service directory.
// It runs automatically before compilation: `cargo build` triggers it.
//
// Requirements:
//   Cargo.toml dependencies:
//     [dependencies]
//     prost = "0.13"
//     prost-types = "0.13"
//
//     [build-dependencies]
//     prost-build = "0.13"
//     tonic-build = "0.12"   # if using gRPC
//
//   System: protoc must be installed (brew install protobuf)
//
// Usage in service code:
//   mod proto {
//       include!(concat!(env!("OUT_DIR"), "/example.v1.rs"));
//   }
//   use proto::{User, UserStatus, UserRole};

fn main() {
    // Tell cargo to recompile if any proto file changes
    println!("cargo:rerun-if-changed=../../packages/schema/proto");

    // Determine proto root (relative to this service's Cargo.toml)
    let proto_root = "../../packages/schema/proto";

    // List all proto files to compile
    // Add your service's proto files alongside the common ones
    let proto_files = [
        // Common types — always include
        "common/v1/errors.proto",
        "common/v1/pagination.proto",
        // Your service's proto files:
        // "[your-service]/v1/[resource].proto",
        // Example:
        "example/v1/user.proto",
    ];

    let proto_paths: Vec<String> = proto_files
        .iter()
        .map(|f| format!("{}/{}", proto_root, f))
        .collect();

    // Option 1: prost-build only (no gRPC)
    prost_build::Config::new()
        // Add serde support for JSON serialization (optional but useful)
        .type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]")
        .type_attribute(".", "#[serde(rename_all = \"camelCase\")]")
        // Compile
        .compile_protos(&proto_paths, &[proto_root])
        .expect("Failed to compile proto files");

    // Option 2: tonic-build (includes gRPC client/server stubs)
    // Comment out Option 1 and uncomment this block:
    //
    // tonic_build::configure()
    //     .type_attribute(".", "#[derive(serde::Serialize, serde::Deserialize)]")
    //     .compile(
    //         &proto_paths,
    //         &[proto_root],
    //     )
    //     .expect("Failed to compile proto files");
}
