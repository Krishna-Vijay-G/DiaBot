"""
DiaBot - Blockchain Service
Immutable audit trail for diagnostic results
"""

import hashlib
import time
import json
import logging
from typing import Dict, List, Optional, Any


class Block:
    """Represents a single block in the blockchain"""
    
    def __init__(self, index: int, timestamp: float, data: Any, 
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of the block"""
        block_string = f"{self.index}{self.timestamp}{json.dumps(self.data, sort_keys=True) if isinstance(self.data, dict) else self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce
        }

    @classmethod
    def from_dict(cls, block_dict: Dict) -> 'Block':
        """Create block from dictionary"""
        # Handle timestamp conversion from string if needed
        timestamp = block_dict['timestamp']
        if isinstance(timestamp, str):
            try:
                timestamp = float(timestamp)
            except ValueError:
                timestamp = time.time()
        
        block = cls(
            block_dict['index'],
            timestamp,
            block_dict['data'],
            block_dict['previous_hash'],
            block_dict.get('nonce', 0)
        )
        block.hash = block_dict['hash']
        return block


class Blockchain:
    """
    Blockchain for medical record audit trail
    Provides immutable storage for diagnostic results
    """
    
    def __init__(self, db_session=None):
        self.chain: List[Block] = []
        self.db_session = db_session
        self._load_from_database()

    def _load_from_database(self):
        """Load blockchain from database"""
        try:
            from flask import has_app_context, current_app
            if not has_app_context():
                self.chain = [self.create_genesis_block()]
                return
            
            # Import models directly to avoid circular import
            from backend.main import BlockchainBlock
            
            db_blocks = BlockchainBlock.query.order_by(BlockchainBlock.index.asc()).all()
            
            if not db_blocks:
                genesis_block = self.create_genesis_block()
                self._save_block_to_database(genesis_block)
                self.chain = [genesis_block]
            else:
                self.chain = [Block.from_dict(block.to_dict()) for block in db_blocks]
        except Exception as e:
            logging.error(f"Error loading blockchain: {str(e)}", exc_info=True)
            self.chain = [self.create_genesis_block()]

    def _save_block_to_database(self, block: Block):
        """Save block to database"""
        try:
            from flask import current_app
            from backend.main import BlockchainBlock, db
            
            db_block = BlockchainBlock(
                index=block.index,
                timestamp=str(block.timestamp),
                data=block.data,
                previous_hash=block.previous_hash,
                hash=block.hash,
                nonce=block.nonce
            )
            db.session.add(db_block)
            db.session.commit()
            logging.info(f"Saved block {block.index} to database")
        except Exception as e:
            logging.error(f"Error saving block to database: {str(e)}", exc_info=True)
            try:
                from backend.main import db
                db.session.rollback()
            except:
                pass

    def create_genesis_block(self) -> Block:
        """Create the genesis block"""
        return Block(0, time.time(), "Genesis Block - DiaBot Medical Records", "0")

    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block"""
        if not self.chain:
            self._load_from_database()
        return self.chain[-1] if self.chain else None

    def add_block(self, data: Any) -> Optional[Block]:
        """Add a new block to the blockchain"""
        try:
            latest_block = self.get_latest_block()
            if not latest_block:
                genesis_block = self.create_genesis_block()
                self._save_block_to_database(genesis_block)
                self.chain = [genesis_block]
                latest_block = genesis_block

            new_block = Block(
                index=latest_block.index + 1,
                timestamp=time.time(),
                data=data,
                previous_hash=latest_block.hash
            )
            
            self._save_block_to_database(new_block)
            self.chain.append(new_block)
            
            logging.info(f"Added block {new_block.index} to blockchain")
            return new_block
        except Exception as e:
            logging.error(f"Error adding block: {str(e)}")
            return None

    def add_diagnostic_record(self, record_data: Dict) -> Optional[Block]:
        """Add diagnostic record to blockchain"""
        return self.add_block({
            'type': 'diagnostic_record',
            'record': record_data,
            'timestamp': time.time()
        })

    def get_chain_length(self) -> int:
        """Get blockchain length"""
        return len(self.chain)

    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        try:
            for i in range(1, len(self.chain)):
                current_block = self.chain[i]
                previous_block = self.chain[i-1]

                if current_block.hash != current_block.calculate_hash():
                    logging.error(f"Invalid hash for block {current_block.index}")
                    return False

                if current_block.previous_hash != previous_block.hash:
                    logging.error(f"Invalid previous hash for block {current_block.index}")
                    return False

            return True
        except Exception as e:
            logging.error(f"Error validating blockchain: {str(e)}")
            return False

    def get_all_records(self) -> List[Dict]:
        """Get all diagnostic records from blockchain"""
        records = []
        for block in self.chain:
            if isinstance(block.data, dict) and block.data.get('type') == 'diagnostic_record':
                records.append(block.data.get('record', {}))
        return records

    def to_dict(self) -> List[Dict]:
        """Convert blockchain to list of dictionaries"""
        return [block.to_dict() for block in self.chain]


# Convenience function
def create_blockchain() -> Blockchain:
    """Create a blockchain instance"""
    return Blockchain()
