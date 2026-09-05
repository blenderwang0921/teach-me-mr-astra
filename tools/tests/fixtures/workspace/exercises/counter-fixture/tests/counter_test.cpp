#include "counter.hpp"
#include <catch2/catch_test_macros.hpp>
#include <limits>
TEST_CASE("empty request") {
    REQUIRE(admit(0, 5) == 0);
    REQUIRE(admit(0, 0) == 0);
}
TEST_CASE("within capacity") {
    REQUIRE(admit(3, 5) == 3);
    REQUIRE(admit(5, 5) == 5);
}
TEST_CASE("capacity boundary") {
    REQUIRE(admit(9, 5) == 5);
    REQUIRE(admit(1, 0) == 0);
    REQUIRE(admit(std::numeric_limits<std::size_t>::max(), 5) == 5);
}
