"""蔬菜数据访问层"""
import logging
from typing import Optional, List, Dict, Any
from app.db.store import run, query, query_one


class VegRepository:
    """蔬菜数据访问类"""
    
    @staticmethod
    def add_vegetable(name: str, category: str = 'other') -> int:
        """
        添加蔬菜
        
        Args:
            name: 蔬菜名称
            category: 风险类别 (high, low, other)
            
        Returns:
            新增记录的ID
        """
        sql = "INSERT INTO Veg (name, category) VALUES (?, ?)"
        try:
            veg_id = run(sql, (name, category))
            logging.info(f"添加蔬菜成功: {name} (ID: {veg_id})")
            return veg_id
        except Exception as e:
            logging.error(f"添加蔬菜失败: {name}, 错误: {e}")
            raise
    
    @staticmethod
    def get_vegetable_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取蔬菜
        
        Args:
            name: 蔬菜名称
            
        Returns:
            蔬菜记录字典，未找到返回None
        """
        sql = "SELECT * FROM Veg WHERE name = ?"
        return query_one(sql, (name,))
    
    @staticmethod
    def get_vegetable_by_id(veg_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取蔬菜
        
        Args:
            veg_id: 蔬菜ID
            
        Returns:
            蔬菜记录字典，未找到返回None
        """
        sql = "SELECT * FROM Veg WHERE id = ?"
        return query_one(sql, (veg_id,))
    
    @staticmethod
    def get_or_create_vegetable(name: str, category: str = 'other') -> int:
        """
        获取或创建蔬菜（如果不存在则创建）
        
        Args:
            name: 蔬菜名称
            category: 风险类别
            
        Returns:
            蔬菜ID
        """
        veg = VegRepository.get_vegetable_by_name(name)
        if veg:
            return veg['id']
        return VegRepository.add_vegetable(name, category)
    
    @staticmethod
    def get_all_vegetables() -> List[Dict[str, Any]]:
        """
        获取所有蔬菜
        
        Returns:
            蔬菜列表
        """
        sql = "SELECT * FROM Veg ORDER BY name"
        return query(sql)
    
    @staticmethod
    def get_vegetables_by_category(category: str) -> List[Dict[str, Any]]:
        """
        根据类别获取蔬菜
        
        Args:
            category: 风险类别
            
        Returns:
            蔬菜列表
        """
        sql = "SELECT * FROM Veg WHERE category = ? ORDER BY name"
        return query(sql, (category,))
    
    @staticmethod
    def update_vegetable(veg_id: int, name: str = None, category: str = None) -> bool:
        """
        更新蔬菜信息
        
        Args:
            veg_id: 蔬菜ID
            name: 新名称（可选）
            category: 新类别（可选）
            
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        
        if category:
            updates.append("category = ?")
            params.append(category)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(veg_id)
        
        sql = f"UPDATE Veg SET {', '.join(updates)} WHERE id = ?"
        try:
            run(sql, tuple(params))
            logging.info(f"更新蔬菜成功: ID={veg_id}")
            return True
        except Exception as e:
            logging.error(f"更新蔬菜失败: ID={veg_id}, 错误: {e}")
            return False
    
    @staticmethod
    def delete_vegetable(veg_id: int) -> bool:
        """
        删除蔬菜
        
        Args:
            veg_id: 蔬菜ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM Veg WHERE id = ?"
        try:
            run(sql, (veg_id,))
            logging.info(f"删除蔬菜成功: ID={veg_id}")
            return True
        except Exception as e:
            logging.error(f"删除蔬菜失败: ID={veg_id}, 错误: {e}")
            return False
