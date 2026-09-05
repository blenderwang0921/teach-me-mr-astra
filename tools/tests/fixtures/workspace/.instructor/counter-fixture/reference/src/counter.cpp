#include "counter.hpp"
std::size_t admit(std::size_t requested, std::size_t capacity) {
    return requested < capacity ? requested : capacity;
}
