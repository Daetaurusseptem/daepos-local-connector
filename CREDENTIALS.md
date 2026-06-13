# 🔐 Credenciales de Prueba - DaePoint POS

Este documento contiene las credenciales generadas por el script `seed.ts` para facilitar las pruebas de la arquitectura multi-sucursal.

> [!IMPORTANT]
> **Contraseña común para todos los usuarios:** `admin123`

---

## 🏗️ Nivel Infraestructura (SysAdmin)
Gestión global de empresas y suscripciones.

| Usuario | Rol | Descripción |
| :--- | :--- | :--- |
| `sysadmin` | `sysadmin` | Acceso total al sistema. |

---

## 🏢 Nivel Corporativo (Company Admin)
Gestión de toda la empresa y sus múltiples sucursales.

| Usuario | Rol | Empresa |
| :--- | :--- | :--- |
| `companyowner` | `companyAdmin` | Super Mercado Premium |
| `corp1` | `admin` | **Corporativo** (Sin sucursal) |

---

## 📍 Nivel Sucursal: Sucursal Centro
Gestión operativa y ventas de una sede específica.

| Usuario | Rol | Sucursal |
| :--- | :--- | :--- |
| `admin` | `admin` | **Gerente** - Sucursal Centro |
| `cajero1` | `user` | Cajero - Sucursal Centro |
| `cajero2` | `user` | Cajero - Sucursal Centro |
| `cajero3` | `user` | Cajero - Sucursal Centro |
| `cajero4` | `user` | Cajero - Sucursal Centro |

---

## 📍 Nivel Sucursal: Sucursal Norte
*Actualmente poblada con inventario pero sin usuarios asignados en el seed (puedes crearlos desde el panel de `companyowner`).*

---

## 📝 Notas de Prueba
1. **Aislamiento**: Si entras como `admin`, solo verás el stock de la *Sucursal Centro*.
2. **Consolidación**: Si entras como `companyowner`, podrás gestionar las sucursales y ver métricas globales.
3. **Ventas**: Los cajeros solo pueden operar si hay una caja física abierta en su sucursal.
