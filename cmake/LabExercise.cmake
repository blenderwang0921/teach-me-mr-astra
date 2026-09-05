include(FetchContent)
# Immutable release commit for Catch2 v3.8.1; cached across lab runs.
FetchContent_Declare(Catch2
  GIT_REPOSITORY https://github.com/catchorg/Catch2.git
  GIT_TAG 56809e5282f104c5c8b570e7c2996cdc352d94f1
  GIT_PROGRESS FALSE
)
set(CATCH_INSTALL_DOCS OFF CACHE BOOL "" FORCE)
set(CATCH_INSTALL_EXTRAS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(Catch2)
list(APPEND CMAKE_MODULE_PATH "${catch2_SOURCE_DIR}/extras")
include(Catch)

function(lab_exercise source)
  file(READ "${source}/spec.json" spec)
  string(JSON standard GET "${spec}" cpp_standard)
  string(JSON timeout GET "${spec}" resource_limits test_timeout_seconds)
  string(JSON seed GET "${spec}" seeds 0)
  if(DEFINED LAB_TEST_SEED)
    set(seed "${LAB_TEST_SEED}")
  endif()
  file(GLOB_RECURSE implementation CONFIGURE_DEPENDS "${source}/src/*.cpp")
  file(GLOB_RECURSE tests CONFIGURE_DEPENDS "${source}/tests/*.cpp")
  if(NOT tests)
    message(FATAL_ERROR "The exercise must provide C++ tests")
  endif()
  add_executable(lab_tests ${implementation} ${tests})
  target_include_directories(lab_tests PRIVATE "${source}/include")
  target_compile_features(lab_tests PRIVATE cxx_std_${standard})
  set_target_properties(lab_tests PROPERTIES CXX_EXTENSIONS OFF)
  target_compile_options(lab_tests PRIVATE -Wall -Wextra -Wpedantic)
  target_link_libraries(lab_tests PRIVATE Catch2::Catch2WithMain)
  find_package(Threads REQUIRED)
  target_link_libraries(lab_tests PRIVATE Threads::Threads)
  if(LAB_SANITIZER AND NOT LAB_SANITIZER STREQUAL "none")
    target_compile_options(lab_tests PRIVATE -fsanitize=${LAB_SANITIZER} -fno-omit-frame-pointer)
    target_link_options(lab_tests PRIVATE -fsanitize=${LAB_SANITIZER})
  endif()
  catch_discover_tests(lab_tests DISCOVERY_MODE PRE_TEST
    WORKING_DIRECTORY "${source}"
    EXTRA_ARGS --rng-seed ${seed}
    PROPERTIES TIMEOUT ${timeout})
endfunction()
