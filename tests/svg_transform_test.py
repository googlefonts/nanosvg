# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from math import degrees, pi
from picosvg.svg_transform import *
from typing import Tuple


@pytest.mark.parametrize(
    "transform, expected_result",
    [
        # translate(tx)
        ("translate(-5)", Affine2D(1, 0, 0, 1, -5, 0)),
        # translate(tx ty)
        ("translate(3.5, -0.65)", Affine2D(1, 0, 0, 1, 3.5, -0.65)),
        # scale(sx)
        ("scale(2)", Affine2D(2, 0, 0, 2, 0, 0)),
        # scale(sx,sy)
        ("scale(-2 -3)", Affine2D(-2, 0, 0, -3, 0, 0)),
        # rotate(angle)
        (f"rotate({degrees(pi / 4)})", Affine2D(0.707, 0.707, -0.707, 0.707, 0, 0)),
        # rotate(angle cx cy)
        (f"rotate({degrees(pi / 2)}, 5, 6)", Affine2D(0, 1, -1, 0, 11, 1)),
        # skewX(angle)
        (f"skewx({degrees(pi / 8)})", Affine2D(1, 0, 0.414, 1, 0, 0)),
        # skewY(angle)
        (f"skewY({degrees(pi / 8)})", Affine2D(1, 0.414, 0, 1, 0, 0)),
        # example from FontTools
        (
            "matrix(2, 0, 0, 3, 1, 6) matrix(4, 3, 2, 1, 5, 6)",
            Affine2D(8, 9, 4, 3, 11, 24),
        ),
        # svg spec example
        # 255 decimal expected part changed from 03 to 061
        (
            "translate(50 90),rotate(-45) translate(130,160)",
            Affine2D(0.707, -0.707, 0.707, 0.707, 255.061, 111.213),
        ),
    ],
)
def test_parse_svg_transform(transform: str, expected_result: Tuple[str, ...]):
    actual = parse_svg_transform(transform)
    print(f"A: {actual}")
    print(f"E: {expected_result}")
    assert actual == pytest.approx(expected_result, 3)


class TestAffine2D:
    def test_map_point(self):
        t = Affine2D(2, 0, 0, 1, 10, 20)
        p = t.map_point((-3, 4))

        assert isinstance(p, Point)
        assert p == Point(4, 24)

        assert Affine2D(1, 0.5, -0.5, 1, 0, 0).map_point(Point(2, 2)) == Point(1.0, 3.0)

    def test_map_vector(self):
        v = Affine2D(2, 0, 0, -1, 0, 0).map_vector((1, 1))
        assert isinstance(v, Vector)
        assert v == Vector(2, -1)

        # vectors are unaffected by translation
        v = Vector(-3, 4)
        assert Affine2D(1, 0, 0, 1, 40, -50).map_vector(v) == v

    def test_determinant(self):
        assert Affine2D(1, 2, 3, 4, 0, 0).determinant() == (1 * 4 - 2 * 3)

    def test_is_degenerate(self):
        assert not Affine2D(1, 2, 3, 4, 5, 6).is_degenerate()
        assert not Affine2D.identity().is_degenerate()
        assert Affine2D.degenerate().is_degenerate()
        assert Affine2D(-1, 2 / 3, 3 / 2, -1, 0, 0).is_degenerate()
        assert Affine2D(
            float_info.epsilon,
            float_info.epsilon,
            float_info.epsilon,
            float_info.epsilon,
            0,
            0,
        ).is_degenerate()

    def test_scale_0_is_degenerate(self):
        assert not Affine2D.identity().scale(1, 1).is_degenerate()
        assert Affine2D.identity().scale(0, 1).is_degenerate()
        assert Affine2D.identity().scale(1, 0).is_degenerate()
        assert Affine2D.identity().scale(0, 0).is_degenerate()

    def test_inverse(self):
        t = Affine2D.identity().translate(2, 3).scale(4, 5)
        p0 = Point(12, 34)
        p1 = t.map_point(p0)
        it = t.inverse()
        p2 = it.map_point(p1)
        assert p2 == p0

        assert Affine2D.degenerate().inverse() == Affine2D.degenerate()
        t = Affine2D(1, 1, 1, 1, 0, 0).inverse()
        assert t.is_degenerate()

    @pytest.mark.parametrize(
        "src, dest, expected",
        [
            ((0, 0, 10, 10), (0, 0, 1000, 1000), (100, 0, 0, 100, 0, 0)),
            ((0, 10, 10, -10), (0, 0, 1000, 1000), (100, 0, 0, -100, 0, 1000)),
            ((0, 0, 0, 0), (0, 0, 1000, 1000), (1, 0, 0, 1, 0, 0)),
            ((0, 0, 10, 10), (0, 0, 0, 1000), (0, 0, 0, 0, 0, 0)),
        ],
    )
    def test_rect_to_rect(self, src, dest, expected):
        assert Affine2D.rect_to_rect(Rect(*src), Rect(*dest)) == Affine2D(*expected)

    def test_rotate_origin(self):
        affine = Affine2D.identity().rotate(pi / 2)
        assert affine.map_point(Point(1, 0)).round(2) == Point(0, 1).round(2)

    def test_product(self):
        affine1 = Affine2D.identity().rotate(pi / 2)
        affine2 = Affine2D.identity().translate(1, 1)
        p0 = Point(1, 1)
        assert Affine2D.product(affine1, affine2).map_point(p0).round(
            2
        ) == affine2.map_point(affine1.map_point(p0)).round(2)

    def test_product_ordering(self):
        affine1 = Affine2D.identity().rotate(pi / 2)
        affine2 = Affine2D.identity().rotate(pi / 2, cx=0, cy=1)

        assert Affine2D.product(affine1, affine2) != Affine2D.product(affine2, affine1)

        # Start at 1,0.
        # Rotate 90° around 0,0 to get 0,1
        # Rotate a further 90° around 0,1 to get ... still 0,1
        # Truly mind blowing stuff.
        p0 = Point(1, 0)
        assert (Affine2D.product(affine1, affine2).map_point(p0).round(2)) == Point(
            0, 1
        ).round(2)

    def test_gettranslate(self):
        af = Affine2D.identity()
        assert af.gettranslate() == (0, 0)
        af = af.translate(1, 2)
        assert af.gettranslate() == (1, 2)
        af = af.translate(2, 3).rotate(pi / 2)
        assert af.gettranslate() == (3, 5)

    def test_getscale(self):
        af = Affine2D.identity()
        assert af.getscale() == (1, 1)
        af = af.scale(2, 3)
        assert af.getscale() == (2, 3)
