#include "counter.hpp"
#include <catch2/catch_test_macros.hpp>
TEST_CASE("extra capacity combinations") {
    for (std::size_t capacity = 0; capacity < 8; ++capacity) {
        for (std::size_t requested = 0; requested < 8; ++requested) {
            const auto result = admit(requested, capacity);
            REQUIRE(result <= capacity);
            REQUIRE(result <= requested);
            REQUIRE((result == capacity || result == requested));
        }
    }
}
