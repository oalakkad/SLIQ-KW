// components/AdminSidebar.tsx
"use client";

import React, { useState, useEffect } from "react";
import { Sidebar, Menu, MenuItem, SubMenu } from "react-pro-sidebar";
import { Box } from "@chakra-ui/react";
import { useRouter, usePathname } from "next/navigation";
import { FaHome, FaShoppingCart, FaBox, FaUsers, FaCog } from "react-icons/fa";
import { FiChevronsLeft, FiChevronsRight } from "react-icons/fi";
import { GrTransaction } from "react-icons/gr";
import { MdDiscount } from "react-icons/md";
import Cookies from "js-cookie";

export default function AdminSidebar() {
  const router = useRouter();
  const pathname = usePathname();

  const [collapsed, setCollapsed] = useState(false);
  const [toggled, setToggled] = useState(false);

  // Load cookie state on mount
  useEffect(() => {
    const savedCollapsed = Cookies.get("sidebar_collapsed");
    if (savedCollapsed === "true") {
      setCollapsed(true);
    }
  }, []);

  const handleCollapsedChange = () => {
    const newValue = !collapsed;
    setCollapsed(newValue);
    // Save the collapsed state in a cookie for 7 days
    Cookies.set("sidebar_collapsed", String(newValue), { expires: 7 });
  };

  return (
    <Box
      height="100vh"
      bg="gray.100"
      boxShadow="md"
      sx={{
        "*": {
          boxSizing: "border-box",
          margin: 0,
          padding: 0,
          fontFamily: '"Montserrat", sans-serif !important',
        },
        "a:hover": {
          color: "white",
          fontSize: "1.1rem",
        },
        ".menu-anchor:hover": {
          backgroundColor: "#f7f2f2 !important",
          fontWeight: "bolder",
        },
        ".menu-label": {
          fontSize: "13px",
        },
        hr: {
          marginTop: 0,
          marginBottom: 0,
          opacity: 0.15,
        },
        ".ps-menu-label": {
          marginLeft: "10px",
        },
        "a, .fpTHfu, .ps-sidebar-container": {
          backgroundColor: "#d6e4f5 !important",
        },
      }}
    >
      <Sidebar
        style={{
          height: "100%",
        }}
        collapsed={collapsed}
        toggled={toggled}
        onBackdropClick={() => setToggled(false)}
      >
        <main>
          {/* Collapse / Expand button */}
          <Menu>
            {collapsed ? (
              <MenuItem
                icon={<FiChevronsRight />}
                onClick={handleCollapsedChange}
              ></MenuItem>
            ) : (
              <MenuItem
                suffix={<FiChevronsLeft />}
                onClick={handleCollapsedChange}
              >
                <div
                  style={{
                    padding: "9px",
                    fontWeight: "bold",
                    fontSize: 14,
                    letterSpacing: "1px",
                  }}
                >
                  ADMIN DASHBOARD
                </div>
              </MenuItem>
            )}
            <hr />
          </Menu>

          {/* Main Menu */}
          <Menu>
            <MenuItem
              icon={<FaHome />}
              active={pathname === "/admin"}
              onClick={() => router.push("/admin")}
            >
              Home
            </MenuItem>

            <MenuItem
              icon={<FaShoppingCart />}
              active={pathname === "/admin/orders"}
              onClick={() => router.push("/admin/orders")}
            >
              Orders
            </MenuItem>

            <MenuItem
              icon={<GrTransaction />}
              active={pathname === "/admin/payments"}
              onClick={() => router.push("/admin/payments")}
            >
              Payments
            </MenuItem>

            <MenuItem
              icon={<MdDiscount />}
              active={pathname === "/admin/discounts"}
              onClick={() => router.push("/admin/discounts")}
            >
              Discounts
            </MenuItem>

            <SubMenu icon={<FaBox />} label="Products" defaultOpen>
              <MenuItem
                active={pathname === "/admin/products"}
                onClick={() => router.push("/admin/products")}
              >
                Products
              </MenuItem>
              <MenuItem
                active={pathname === "/admin/categories"}
                onClick={() => router.push("/admin/categories")}
              >
                Categories
              </MenuItem>
              <MenuItem
                active={pathname === "/admin/addons"}
                onClick={() => router.push("/admin/addons")}
              >
                Addons
              </MenuItem>
              <MenuItem
                active={pathname === "/admin/addon-categories"}
                onClick={() => router.push("/admin/addon-categories")}
              >
                Addon Categories
              </MenuItem>
            </SubMenu>

            <MenuItem
              icon={<FaUsers />}
              active={pathname === "/admin/customers"}
              onClick={() => router.push("/admin/customers")}
            >
              Customers
            </MenuItem>

            <MenuItem
              icon={<FaCog />}
              active={pathname === "/admin/settings"}
              onClick={() => router.push("/admin/settings")}
            >
              Settings
            </MenuItem>
          </Menu>
        </main>
      </Sidebar>
    </Box>
  );
}
