"""价格历史数据访问层"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.store import run, query, query_one
from app.db.veg_repository import VegRepository
from app.db.unit_repository import UnitRepository


class PriceHistoryRepository:
    """价格历史数据访问类"""
    
    @staticmethod
    def add_price(vegetable_name: str, unit_name: str, price: float, 
                  date: str = None, source: str = None) -> int:
        """
        添加价格记录
        
        Args:
            vegetable_name: 蔬菜名称
            unit_name: 单位名称
            price: 价格
            date: 日期（格式：YYYY-MM-DD），默认为今天
            source: 数据来源
            
        Returns:
            新增记录的ID
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 获取或创建蔬菜和单位
        veg_id = VegRepository.get_or_create_vegetable(vegetable_name)
        unit_id = UnitRepository.get_or_create_unit(unit_name)
        
        sql = """INSERT INTO PriceHistory (vegetable_id, unit_id, price, date, source) 
                 VALUES (?, ?, ?, ?, ?)"""
        try:
            price_id = run(sql, (veg_id, unit_id, price, date, source))
            logging.info(f"添加价格记录成功: {vegetable_name} @ {unit_name} = {price} (ID: {price_id})")
            return price_id
        except Exception as e:
            logging.error(f"添加价格记录失败: {vegetable_name}, 错误: {e}")
            raise
    
    @staticmethod
    def get_price_by_id(price_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取价格记录
        
        Args:
            price_id: 价格记录ID
            
        Returns:
            价格记录字典（包含蔬菜和单位名称）
        """
        sql = """
            SELECT ph.*, v.name as vegetable_name, u.name as unit_name
            FROM PriceHistory ph
            JOIN Veg v ON ph.vegetable_id = v.id
            JOIN Unit u ON ph.unit_id = u.id
            WHERE ph.id = ?
        """
        return query_one(sql, (price_id,))
    
    @staticmethod
    def get_latest_price(vegetable_name: str, unit_name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定蔬菜和单位的最新价格
        
        Args:
            vegetable_name: 蔬菜名称
            unit_name: 单位名称
            
        Returns:
            最新价格记录字典，未找到返回None
        """
        sql = """
            SELECT ph.*, v.name as vegetable_name, u.name as unit_name
            FROM PriceHistory ph
            JOIN Veg v ON ph.vegetable_id = v.id
            JOIN Unit u ON ph.unit_id = u.id
            WHERE v.name = ? AND u.name = ?
            ORDER BY ph.date DESC, ph.created_at DESC
            LIMIT 1
        """
        return query_one(sql, (vegetable_name, unit_name))
    
    @staticmethod
    def get_price_history(vegetable_name: str, unit_name: str = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取价格历史记录
        
        Args:
            vegetable_name: 蔬菜名称
            unit_name: 单位名称（可选）
            limit: 返回记录数限制
            
        Returns:
            价格历史记录列表
        """
        if unit_name:
            sql = """
                SELECT ph.*, v.name as vegetable_name, u.name as unit_name
                FROM PriceHistory ph
                JOIN Veg v ON ph.vegetable_id = v.id
                JOIN Unit u ON ph.unit_id = u.id
                WHERE v.name = ? AND u.name = ?
                ORDER BY ph.date DESC, ph.created_at DESC
                LIMIT ?
            """
            return query(sql, (vegetable_name, unit_name, limit))
        else:
            sql = """
                SELECT ph.*, v.name as vegetable_name, u.name as unit_name
                FROM PriceHistory ph
                JOIN Veg v ON ph.vegetable_id = v.id
                JOIN Unit u ON ph.unit_id = u.id
                WHERE v.name = ?
                ORDER BY ph.date DESC, ph.created_at DESC
                LIMIT ?
            """
            return query(sql, (vegetable_name, limit))
    
    @staticmethod
    def get_prices_by_date(date: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的所有价格记录
        
        Args:
            date: 日期（格式：YYYY-MM-DD）
            
        Returns:
            价格记录列表
        """
        sql = """
            SELECT ph.*, v.name as vegetable_name, u.name as unit_name
            FROM PriceHistory ph
            JOIN Veg v ON ph.vegetable_id = v.id
            JOIN Unit u ON ph.unit_id = u.id
            WHERE ph.date = ?
            ORDER BY v.name, u.name
        """
        return query(sql, (date,))
    
    @staticmethod
    def update_price(price_id: int, price: float = None, date: str = None, 
                     source: str = None) -> bool:
        """
        更新价格记录
        
        Args:
            price_id: 价格记录ID
            price: 新价格（可选）
            date: 新日期（可选）
            source: 新来源（可选）
            
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if price is not None:
            updates.append("price = ?")
            params.append(price)
        
        if date:
            updates.append("date = ?")
            params.append(date)
        
        if source is not None:
            updates.append("source = ?")
            params.append(source)
        
        if not updates:
            return False
        
        params.append(price_id)
        sql = f"UPDATE PriceHistory SET {', '.join(updates)} WHERE id = ?"
        
        try:
            run(sql, tuple(params))
            logging.info(f"更新价格记录成功: ID={price_id}")
            return True
        except Exception as e:
            logging.error(f"更新价格记录失败: ID={price_id}, 错误: {e}")
            return False
    
    @staticmethod
    def delete_price(price_id: int) -> bool:
        """
        删除价格记录
        
        Args:
            price_id: 价格记录ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM PriceHistory WHERE id = ?"
        try:
            run(sql, (price_id,))
            logging.info(f"删除价格记录成功: ID={price_id}")
            return True
        except Exception as e:
            logging.error(f"删除价格记录失败: ID={price_id}, 错误: {e}")
            return False
    
    @staticmethod
    def get_price_statistics(vegetable_name: str, unit_name: str = None) -> Dict[str, Any]:
        """
        获取价格统计信息
        
        Args:
            vegetable_name: 蔬菜名称
            unit_name: 单位名称（可选）
            
        Returns:
            统计信息字典（包含最新价、最高价、最低价、平均价等）
        """
        if unit_name:
            sql = """
                SELECT 
                    COUNT(*) as count,
                    MIN(ph.price) as min_price,
                    MAX(ph.price) as max_price,
                    AVG(ph.price) as avg_price,
                    MIN(ph.date) as first_date,
                    MAX(ph.date) as last_date
                FROM PriceHistory ph
                JOIN Veg v ON ph.vegetable_id = v.id
                JOIN Unit u ON ph.unit_id = u.id
                WHERE v.name = ? AND u.name = ?
            """
            result = query_one(sql, (vegetable_name, unit_name))
        else:
            sql = """
                SELECT 
                    COUNT(*) as count,
                    MIN(ph.price) as min_price,
                    MAX(ph.price) as max_price,
                    AVG(ph.price) as avg_price,
                    MIN(ph.date) as first_date,
                    MAX(ph.date) as last_date
                FROM PriceHistory ph
                JOIN Veg v ON ph.vegetable_id = v.id
                WHERE v.name = ?
            """
            result = query_one(sql, (vegetable_name,))
        
        if result:
            # 获取最新价格
            latest = PriceHistoryRepository.get_latest_price(vegetable_name, unit_name)
            result['latest_price'] = latest['price'] if latest else None
            result['latest_date'] = latest['date'] if latest else None
        
        return result or {}
