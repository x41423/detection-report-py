"""单位数据访问层"""
import logging
from typing import Optional, List, Dict, Any
from app.db.store import run, query, query_one


class UnitRepository:
    """单位数据访问类"""
    
    @staticmethod
    def add_unit(name: str, description: str = None) -> int:
        """
        添加单位
        
        Args:
            name: 单位名称
            description: 单位描述
            
        Returns:
            新增记录的ID
        """
        sql = "INSERT INTO Unit (name, description) VALUES (?, ?)"
        try:
            unit_id = run(sql, (name, description))
            logging.info(f"添加单位成功: {name} (ID: {unit_id})")
            return unit_id
        except Exception as e:
            logging.error(f"添加单位失败: {name}, 错误: {e}")
            raise
    
    @staticmethod
    def get_unit_by_name(name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取单位
        
        Args:
            name: 单位名称
            
        Returns:
            单位记录字典，未找到返回None
        """
        sql = "SELECT * FROM Unit WHERE name = ?"
        return query_one(sql, (name,))
    
    @staticmethod
    def get_unit_by_id(unit_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单位
        
        Args:
            unit_id: 单位ID
            
        Returns:
            单位记录字典，未找到返回None
        """
        sql = "SELECT * FROM Unit WHERE id = ?"
        return query_one(sql, (unit_id,))
    
    @staticmethod
    def get_or_create_unit(name: str, description: str = None) -> int:
        """
        获取或创建单位（如果不存在则创建）
        
        Args:
            name: 单位名称
            description: 单位描述
            
        Returns:
            单位ID
        """
        unit = UnitRepository.get_unit_by_name(name)
        if unit:
            return unit['id']
        return UnitRepository.add_unit(name, description)
    
    @staticmethod
    def get_all_units() -> List[Dict[str, Any]]:
        """
        获取所有单位
        
        Returns:
            单位列表
        """
        sql = "SELECT * FROM Unit ORDER BY name"
        return query(sql)
    
    @staticmethod
    def update_unit(unit_id: int, name: str = None, description: str = None) -> bool:
        """
        更新单位信息
        
        Args:
            unit_id: 单位ID
            name: 新名称（可选）
            description: 新描述（可选）
            
        Returns:
            是否更新成功
        """
        updates = []
        params = []
        
        if name:
            updates.append("name = ?")
            params.append(name)
        
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if not updates:
            return False
        
        params.append(unit_id)
        sql = f"UPDATE Unit SET {', '.join(updates)} WHERE id = ?"
        
        try:
            run(sql, tuple(params))
            logging.info(f"更新单位成功: ID={unit_id}")
            return True
        except Exception as e:
            logging.error(f"更新单位失败: ID={unit_id}, 错误: {e}")
            return False
    
    @staticmethod
    def delete_unit(unit_id: int) -> bool:
        """
        删除单位
        
        Args:
            unit_id: 单位ID
            
        Returns:
            是否删除成功
        """
        sql = "DELETE FROM Unit WHERE id = ?"
        try:
            run(sql, (unit_id,))
            logging.info(f"删除单位成功: ID={unit_id}")
            return True
        except Exception as e:
            logging.error(f"删除单位失败: ID={unit_id}, 错误: {e}")
            return False
